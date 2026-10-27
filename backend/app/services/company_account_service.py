"""Account identity and payment attribution; never changes payment amounts."""
import json
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import exists, or_, select, text, update

from app.core.deps import get_current_user
from app.core.permissions import user_has_permission
from app.models.company_account import CompanyAccount
from app.models.outsource import OutsourcePayment
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost


async def require_account_selection(request: Request, current_user=Depends(get_current_user)):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if request.method not in {"POST", "PUT", "PATCH"}:
        return
    if content_type and content_type != "application/json" and not content_type.endswith("+json"):
        return
    raw = await request.body()
    if not raw:
        return
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(422, "请求 JSON 格式无效") from exc
    if isinstance(body, dict) and body.get("payment_account_id") and not user_has_permission(current_user, "company_account:select"):
        raise HTTPException(403, "没有选择付款账户的权限")


class CompanyAccountService:
    def __init__(self, db):
        self.db = db

    async def _serialize_changes(self):
        # Serializes default/name edits, including insertion into an empty table.
        await self.db.execute(text("SELECT pg_advisory_xact_lock(720261027)"))

    async def is_referenced(self, account_id):
        checks = [exists(select(model.id).where(model.payment_account_id == account_id))
                  for model in (Expense, ProjectCost, PayablePayment, OutsourcePayment)]
        return bool(await self.db.scalar(select(or_(*checks))))

    @staticmethod
    def payload(account, *, full=False, referenced=False):
        number = account.account_number
        tail = number[-4:] if number and len(number) > 4 else None
        masked = "****" + (tail or "") if number else None
        return {
            "id": str(account.id), "name": account.name, "account_type": account.account_type,
            "holder_name": account.holder_name if full else None,
            "bank_name": account.bank_name,
            "account_number": number if full else None, "masked_number": masked,
            "label": account.name + (f"（尾号 {tail}）" if tail else "（账号已隐藏）" if number else ""),
            "is_active": account.is_active, "is_default": account.is_default,
            "remark": account.remark, "is_referenced": referenced,
        }

    async def list_accounts(self, *, options=False, full=False, include_inactive=False):
        query = select(CompanyAccount).order_by(CompanyAccount.is_default.desc(), CompanyAccount.name)
        if options and not include_inactive:
            query = query.where(CompanyAccount.is_active.is_(True))
        accounts = (await self.db.execute(query)).scalars().all()
        rows = []
        for account in accounts:
            row = self.payload(account, full=full, referenced=await self.is_referenced(account.id) if not options else False)
            if options:
                row = {key: row[key] for key in ("id", "name", "account_type", "label", "masked_number", "is_default", "is_active")}
            rows.append(row)
        return rows

    @staticmethod
    def _validate(data):
        data = {key: value.strip() if isinstance(value, str) else value for key, value in data.items()}
        for key in ("holder_name", "bank_name", "account_number", "remark"):
            if data.get(key) == "":
                data[key] = None
        if not data.get("name"):
            raise ValueError("账户名称不能为空")
        if any(data.get(key) is None for key in ("is_active", "is_default")):
            raise ValueError("账户状态和默认状态不能为空")
        kind = data.get("account_type")
        if kind not in {"bank", "wechat", "alipay", "cash", "other"}:
            raise ValueError("账户类型无效")
        if kind in {"bank", "wechat", "alipay"} and not data.get("account_number"):
            raise ValueError("请填写账号")
        if kind == "bank" and (not data.get("holder_name") or not data.get("bank_name")):
            raise ValueError("银行账户请填写开户名称和开户行")
        if kind == "cash":
            data.update(account_number=None, holder_name=None, bank_name=None)
        if not data.get("is_active", True):
            data["is_default"] = False
        return data

    async def save(self, data, account_id=None, *, full=False):
        await self._serialize_changes()
        account = None
        referenced = False
        if account_id:
            account = await self.db.scalar(select(CompanyAccount).where(CompanyAccount.id == account_id).with_for_update())
            if not account:
                raise ValueError("公司账户不存在")
            referenced = await self.is_referenced(account.id)
        previous = {key: getattr(account, key) for key in (
            "name", "account_type", "holder_name", "bank_name", "account_number", "is_active", "is_default", "remark",
        )} if account else {"is_active": True, "is_default": False}
        normalized = self._validate({**previous, **data})
        if referenced and any(normalized[key] != previous[key] for key in ("account_type", "holder_name", "bank_name", "account_number")):
            raise ValueError("该账户已有付款关联，不能修改账户身份；请新建账户并停用旧账户")
        duplicate = await self.db.scalar(select(CompanyAccount.id).where(
            CompanyAccount.name == normalized["name"], CompanyAccount.id != account_id if account_id else text("true"),
        ))
        if duplicate:
            raise ValueError("账户名称已存在")
        if normalized.get("is_default"):
            await self.db.execute(update(CompanyAccount).where(CompanyAccount.is_default.is_(True)).values(is_default=False))
            await self.db.flush()
        if account is None:
            account = CompanyAccount(**normalized)
            self.db.add(account)
        else:
            for key, value in normalized.items():
                setattr(account, key, value)
        await self.db.flush()
        return self.payload(account, full=full, referenced=referenced)

    async def delete(self, account_id):
        await self._serialize_changes()
        account = await self.db.scalar(select(CompanyAccount).where(CompanyAccount.id == account_id).with_for_update())
        if not account:
            raise ValueError("公司账户不存在")
        if await self.is_referenced(account_id):
            raise ValueError("该账户已有付款关联，请停用账户以保留历史记录")
        await self.db.delete(account)
        await self.db.flush()

    async def resolve(self, account_id):
        if not account_id:
            raise ValueError("请选择付款账户")
        try:
            account_id = UUID(str(account_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("付款账户无效，请重新选择") from exc
        account = await self.db.scalar(select(CompanyAccount).where(
            CompanyAccount.id == account_id,
        ).with_for_update())
        if not account or not account.is_active:
            raise ValueError("付款账户不存在或已停用，请重新选择")
        return account.id

    async def initial_account(self, data, initial_paid, *, current=None, payment_changed=True):
        """Allow unrelated edits of historical/unavailable accounts, never new cash without one."""
        account_id = data.get("payment_account_id", getattr(current, "payment_account_id", None))
        if Decimal(str(initial_paid)) <= 0:
            return None
        unchanged = current is not None and str(account_id) == str(getattr(current, "payment_account_id", None))
        if unchanged and not payment_changed:
            return account_id
        return await self.resolve(account_id)
