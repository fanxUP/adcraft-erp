from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_all_permissions, require_any_permission, require_permission, user_has_permission
from app.models.outsource import OutsourcePayment
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.schemas.common import error, success
from app.schemas.company_account import CompanyAccountCreate, CompanyAccountUpdate, PaymentAccountAssignment
from app.services.company_account_service import CompanyAccountService
from app.services.operation_log_service import log_operation

router = APIRouter(prefix="/company-accounts", tags=["Company accounts"])


async def _audit(db, user, request, object_id, action, data):
    # Never write full bank details to operation logs.
    await log_operation(db, user.id, user.real_name or user.username, "company_account", object_id,
                        action, ip_address=request.client.host if request.client else None, after_data=data)


@router.get("/options")
async def options(include_inactive: bool = False, db: AsyncSession = Depends(get_db), user=Depends(require_any_permission("company_account:select", "company_account:read"))):
    return success(await CompanyAccountService(db).list_accounts(options=True, include_inactive=include_inactive))


@router.get("/")
async def list_accounts(db: AsyncSession = Depends(get_db), user=Depends(require_permission("company_account:read"))):
    return success(await CompanyAccountService(db).list_accounts(full=user_has_permission(user, "company_account:view_number")))


@router.post("/")
async def create_account(data: CompanyAccountCreate, request: Request, db: AsyncSession = Depends(get_db), user=Depends(require_all_permissions("company_account:manage", "company_account:read", "company_account:view_number"))):
    try:
        account = await CompanyAccountService(db).save(data.model_dump(), full=user_has_permission(user, "company_account:view_number"))
    except ValueError as exc:
        return error(40001, str(exc))
    await _audit(db, user, request, UUID(account["id"]), "create", {"name": account["name"], "account_type": account["account_type"]})
    return success(account)


@router.put("/{account_id}")
async def update_account(account_id: UUID, data: CompanyAccountUpdate, request: Request, db: AsyncSession = Depends(get_db), user=Depends(require_all_permissions("company_account:manage", "company_account:read", "company_account:view_number"))):
    try:
        account = await CompanyAccountService(db).save(data.model_dump(exclude_unset=True), account_id, full=user_has_permission(user, "company_account:view_number"))
    except ValueError as exc:
        return error(40001, str(exc))
    await _audit(db, user, request, account_id, "update", {key: account[key] for key in ("name", "is_active", "is_default")})
    return success(account)


@router.delete("/{account_id}")
async def delete_account(account_id: UUID, request: Request, db: AsyncSession = Depends(get_db), user=Depends(require_all_permissions("company_account:manage", "company_account:read", "company_account:view_number"))):
    try:
        await CompanyAccountService(db).delete(account_id)
    except ValueError as exc:
        return error(40001, str(exc))
    await _audit(db, user, request, account_id, "delete", {})
    return success({"deleted": True})


@router.put("/assignments/{kind}/{record_id}")
async def assign_payment_account(kind: str, record_id: UUID, data: PaymentAccountAssignment, request: Request,
                                 db: AsyncSession = Depends(get_db), user=Depends(require_permission("company_account:select"))):
    models = {"expense": Expense, "project_cost": ProjectCost, "payable_payment": PayablePayment, "outsource_payment": OutsourcePayment}
    model = models.get(kind)
    if model is None:
        raise HTTPException(422, "付款来源无效")
    required = "outsource_payment:create" if kind == "outsource_payment" else "expense:update"
    if not user_has_permission(user, required):
        raise HTTPException(403, "没有修改该来源付款账户的权限")
    query = select(model).where(model.id == record_id).with_for_update(of=model)
    record = await db.scalar(query)
    if record is None or getattr(record, "deleted_at", None) or getattr(record, "is_voided", False):
        return error(40001, "付款记录不存在、已删除或已撤销")
    if kind in {"expense", "project_cost"}:
        debt = record.payable_amount if kind == "expense" else record.debt_amount
        if record.amount - (debt or 0) <= 0:
            return error(40001, "该来源没有登记时已付金额")
    if kind == "payable_payment":
        source_model = Expense if record.source_type == "expense" else ProjectCost
        source = await db.scalar(select(source_model.id).where(source_model.id == record.source_id, source_model.deleted_at.is_(None)))
        if source is None:
            return error(40001, "付款来源已删除")
    previous = str(record.payment_account_id) if record.payment_account_id else None
    try:
        record.payment_account_id = await CompanyAccountService(db).resolve(data.payment_account_id)
    except ValueError as exc:
        return error(40001, str(exc))
    await db.flush()
    await _audit(db, user, request, record_id, "assign_payment_account", {
        "source_kind": kind, "previous_account_id": previous, "payment_account_id": str(record.payment_account_id),
    })
    return success({"updated": True})
