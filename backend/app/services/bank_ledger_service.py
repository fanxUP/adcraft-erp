"""Account-level cash ledger assembled from ERP payments and manual movements."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select, text

from app.models.business_document import BusinessDocument
from app.models.bank_ledger import BankLedgerEntry
from app.models.company_account import CompanyAccount
from app.models.outsource import OutsourceVendor
from app.services.expenditure_service import ExpenditureService

SUPPORTED_ACCOUNT_TYPES = {"bank", "wechat", "alipay"}
MONEY_ZERO = Decimal("0.00")


class BankLedgerService:
    def __init__(self, db, viewer):
        self.db = db
        self.viewer = viewer

    @staticmethod
    def _today():
        return datetime.now(ZoneInfo("Asia/Shanghai")).date()

    @staticmethod
    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    @staticmethod
    def _amount_value(value):
        return float(BankLedgerService._money(value))

    async def _account(self, account_id, *, lock=False):
        query = select(CompanyAccount).where(CompanyAccount.id == account_id)
        if lock:
            query = query.with_for_update()
        account = await self.db.scalar(query)
        if account is None:
            raise ValueError("公司账户不存在")
        if account.account_type not in SUPPORTED_ACCOUNT_TYPES:
            raise ValueError("银行台账仅支持银行、微信和支付宝账户")
        return account

    @staticmethod
    def _opening_payload(entry):
        if entry is None:
            return None
        return {
            "entry_date": entry.entry_date.isoformat(),
            "amount": BankLedgerService._amount_value(entry.amount),
        }

    async def get_ledger(self, account_id: UUID, page=1, page_size=20):
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        await self._account(account_id)
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        opening_date = opening.entry_date if opening else None

        cash_payments = await ExpenditureService(self.db, self.viewer).list_account_cash_payments(
            account_id, start_date=opening_date,
        )
        manual_query = select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "manual",
        )
        if opening_date:
            manual_query = manual_query.where(BankLedgerEntry.entry_date >= opening_date)
        manual_entries = (await self.db.execute(
            manual_query.order_by(BankLedgerEntry.entry_date.asc(), BankLedgerEntry.created_at.asc())
        )).scalars().all()

        rows = []
        for payment in cash_payments:
            paid_at = payment["paid_at"]
            row_date = paid_at.date()
            amount = self._money(payment["amount"])
            rows.append({
                "id": str(payment["row_key"]),
                "entry_type": "source_payment",
                "source_label": {
                    "expense": "费用付款",
                    "project_cost": "项目成本付款",
                    "outsource_task": "外协付款",
                    "outsource_payment": "外协付款",
                }.get(payment["source_kind"], "ERP付款"),
                "source_kind": payment["source_kind"],
                "source_id": str(payment["source_id"]),
                "document_id": str(payment["document_id"]) if payment["document_id"] else None,
                "document_type": payment["document_type"],
                "entry_date": row_date.isoformat(),
                "summary": payment.get("description") or payment.get("source_no") or "已登记付款",
                "counterparty_account": None,
                "counterparty_name": payment.get("supplier_name"),
                "category": payment.get("category"),
                "income_amount": MONEY_ZERO,
                "expense_amount": amount,
                "balance": None,
                "project_name": payment.get("project_name"),
                "department": payment.get("department"),
                "_sort": (row_date, 1, paid_at.isoformat(), str(payment["row_key"])),
            })
        for entry in manual_entries:
            amount = self._money(entry.amount)
            is_income = entry.direction == "income"
            rows.append({
                "id": str(entry.id),
                "entry_type": "manual",
                "source_label": "手工登记",
                "entry_date": entry.entry_date.isoformat(),
                "summary": entry.summary,
                "counterparty_account": entry.counterparty_account,
                "counterparty_name": entry.counterparty_name,
                "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
                "category": entry.category,
                "income_amount": amount if is_income else MONEY_ZERO,
                "expense_amount": MONEY_ZERO if is_income else amount,
                "balance": None,
                "project_name": entry.project_name,
                "department": entry.department,
                "order_id": str(entry.order_id) if entry.order_id else None,
                "_sort": (
                    entry.entry_date,
                    2,
                    entry.created_at.isoformat() if entry.created_at else "",
                    str(entry.id),
                ),
            })

        opening_amount = self._money(opening.amount) if opening else None
        if opening:
            rows.append({
                "id": "opening:" + str(opening.id),
                "entry_type": "opening_balance",
                "source_label": "期初",
                "entry_date": opening.entry_date.isoformat(),
                "summary": "期初余额",
                "counterparty_account": None,
                "counterparty_name": None,
                "category": "期初余额",
                "income_amount": MONEY_ZERO,
                "expense_amount": MONEY_ZERO,
                "balance": opening_amount,
                "project_name": None,
                "department": None,
                "_sort": (opening.entry_date, 0, "", str(opening.id)),
            })

        rows.sort(key=lambda row: row["_sort"])
        balance = opening_amount
        income_total = MONEY_ZERO
        expense_total = MONEY_ZERO
        for row in rows:
            if row["entry_type"] == "opening_balance":
                row["balance"] = balance
            else:
                income = self._money(row["income_amount"])
                expense = self._money(row["expense_amount"])
                income_total += income
                expense_total += expense
                if balance is not None:
                    balance += income - expense
                    row["balance"] = balance
            row["income_amount"] = self._amount_value(row["income_amount"])
            row["expense_amount"] = self._amount_value(row["expense_amount"])
            row["balance"] = self._amount_value(row["balance"]) if row["balance"] is not None else None

        display_rows = []
        for row_date in sorted({row["entry_date"] for row in rows}, reverse=True):
            day_rows = [row for row in rows if row["entry_date"] == row_date]
            opening_rows = [row for row in day_rows if row["entry_type"] == "opening_balance"]
            transaction_rows = sorted(
                (row for row in day_rows if row["entry_type"] != "opening_balance"),
                key=lambda row: row["_sort"],
                reverse=True,
            )
            display_rows.extend(opening_rows + transaction_rows)
        rows = display_rows
        for row in rows:
            row.pop("_sort", None)
        total = len(rows)
        start = (page - 1) * page_size
        page_rows = rows[start:start + page_size]
        return {
            "items": page_rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "opening_balance": self._opening_payload(opening),
            "summary": {
                "opening_balance": self._amount_value(opening_amount) if opening_amount is not None else None,
                "income_amount": self._amount_value(income_total),
                "expense_amount": self._amount_value(expense_total),
                "balance": self._amount_value(balance) if balance is not None else None,
                "transaction_count": max(total - (1 if opening else 0), 0),
            },
        }

    async def set_opening_balance(self, account_id: UUID, data: dict, created_by: UUID):
        account = await self._account(account_id, lock=True)
        entry_date = data["entry_date"]
        amount = self._money(data["amount"])
        if entry_date > self._today():
            raise ValueError("期初日期不能晚于今天")
        manual_before_opening = await self.db.scalar(select(exists().where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "manual",
            BankLedgerEntry.entry_date < entry_date,
        )))
        if manual_before_opening:
            raise ValueError("期初日期不能晚于已登记的手工流水日期")
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "opening_balance",
        ).with_for_update())
        before = {
            "entry_date": opening.entry_date.isoformat(),
            "amount": self._amount_value(opening.amount),
        } if opening else None
        if opening is None:
            opening = BankLedgerEntry(
                account_id=account.id,
                entry_type="opening_balance",
                direction="opening",
                entry_date=entry_date,
                amount=amount,
                summary="期初余额",
                created_by=created_by,
            )
            self.db.add(opening)
        else:
            opening.entry_date = entry_date
            opening.amount = amount
        await self.db.flush()
        return opening, before

    async def create_entry(self, account_id: UUID, data: dict, created_by: UUID):
        request_id = data["request_id"]
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": "bank-ledger-request:" + str(request_id)},
        )
        account = await self._account(account_id, lock=True)
        existing = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.request_id == request_id,
        ).with_for_update())
        if existing:
            if existing.account_id != account_id:
                raise ValueError("该流水请求编号已被另一账户使用")
            return existing, False
        if not account.is_active:
            raise ValueError("已停用账户不能登记新流水")
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        if opening is None:
            raise ValueError("请先设置该账户的期初余额")
        entry_date = data["entry_date"]
        if entry_date > self._today():
            raise ValueError("流水日期不能晚于今天")
        if entry_date < opening.entry_date:
            raise ValueError("流水日期不能早于期初日期")

        values = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in data.items()
        }
        for key in ("counterparty_account", "counterparty_name", "category", "project_name", "department"):
            if values.get(key) == "":
                values[key] = None
        if not values.get("summary"):
            raise ValueError("摘要不能为空")

        supplier_id = values.get("counterparty_supplier_id")
        if supplier_id:
            supplier = await self.db.scalar(select(OutsourceVendor).where(
                OutsourceVendor.id == supplier_id,
                OutsourceVendor.deleted_at.is_(None),
                OutsourceVendor.is_active.is_(True),
            ))
            if supplier is None:
                raise ValueError("供应商不存在或已停用，请重新选择")
            values["counterparty_name"] = supplier.name

        order_id = values.get("order_id")
        if order_id:
            order = await self.db.scalar(select(BusinessDocument).where(
                BusinessDocument.id == order_id,
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
            ))
            if order is None:
                raise ValueError("订单不存在或已删除，请重新选择")
            values["project_name"] = order.project_name
            values["department"] = order.department

        entry = BankLedgerEntry(
            account_id=account.id,
            entry_type="manual",
            direction=values["direction"],
            entry_date=entry_date,
            amount=self._money(values["amount"]),
            summary=values["summary"],
            counterparty_account=values.get("counterparty_account"),
            counterparty_name=values.get("counterparty_name"),
            counterparty_supplier_id=supplier_id,
            category=values.get("category"),
            project_name=values.get("project_name"),
            department=values.get("department"),
            order_id=order_id,
            request_id=request_id,
            created_by=created_by,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry, True

    @staticmethod
    def entry_payload(entry):
        return {
            "id": str(entry.id),
            "account_id": str(entry.account_id),
            "entry_type": entry.entry_type,
            "direction": entry.direction,
            "entry_date": entry.entry_date.isoformat(),
            "amount": BankLedgerService._amount_value(entry.amount),
            "summary": entry.summary,
            "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
            "order_id": str(entry.order_id) if entry.order_id else None,
        }
