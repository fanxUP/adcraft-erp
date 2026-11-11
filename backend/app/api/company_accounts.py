from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_COMPANY_ACCOUNT_LEDGER_CREATE,
    PERM_COMPANY_ACCOUNT_LEDGER_READ,
    PERM_COMPANY_ACCOUNT_OPENING_BALANCE_SET,
    require_all_permissions,
    require_any_permission,
    require_permission,
    user_has_permission,
)
from app.models.business_document import BusinessDocument
from app.models.outsource import OutsourcePayment, OutsourceVendor
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.schemas.common import error, success
from app.schemas.company_account import (
    BankLedgerEntryCreate,
    BankLedgerEntryUpdate,
    BankProjectCostCreate,
    BankCustomerReceiptCreate,
    CompanyAccountCreate,
    CompanyAccountUpdate,
    OpeningBalanceSet,
    PaymentAccountAssignment,
)
from app.services.bank_ledger_service import BankLedgerService
from app.services.business_document_service import ORDER_ITEM_MUTABLE_STATUSES
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


@router.get("/ledger-options/suppliers")
async def bank_ledger_supplier_options(
    keyword: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_CREATE)),
):
    query = select(OutsourceVendor).where(
        OutsourceVendor.deleted_at.is_(None),
        OutsourceVendor.is_active.is_(True),
    )
    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.where(or_(
            OutsourceVendor.name.ilike(search),
            OutsourceVendor.short_name.ilike(search),
            OutsourceVendor.vendor_no.ilike(search),
        ))
    suppliers = (await db.execute(
        query.order_by(OutsourceVendor.name.asc(), OutsourceVendor.vendor_no.asc()).limit(50)
    )).scalars().all()
    return success([{"id": str(item.id), "name": item.name, "vendor_no": item.vendor_no} for item in suppliers])


@router.get("/ledger-options/orders")
async def bank_ledger_order_options(
    keyword: str | None = Query(default=None, max_length=100),
    purpose: Literal["manual", "project_cost", "receipt"] = "manual",
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_CREATE)),
):
    query = select(BusinessDocument).where(
        BusinessDocument.doc_type == "order",
        BusinessDocument.deleted_at.is_(None),
    )
    if purpose == "project_cost":
        query = query.where(BusinessDocument.status.in_(ORDER_ITEM_MUTABLE_STATUSES - {"completed"}))
    elif purpose == "receipt":
        query = query.where(
            BusinessDocument.status.not_in(("pending_confirm", "cancelled")),
            BusinessDocument.customer_id.is_not(None),
        )
    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.where(or_(
            BusinessDocument.doc_no.ilike(search),
            BusinessDocument.project_name.ilike(search),
            BusinessDocument.department.ilike(search),
        ))
    orders = (await db.execute(
        query.order_by(BusinessDocument.order_date.desc().nullslast(), BusinessDocument.created_at.desc()).limit(50)
    )).scalars().all()
    return success([{
        "id": str(item.id),
        "doc_no": item.doc_no,
        "project_name": item.project_name,
        "department": item.department,
    } for item in orders])


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


@router.get("/{account_id}/ledger")
async def list_account_ledger(
    account_id: UUID,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_READ)),
):
    try:
        result = await BankLedgerService(db, user).get_ledger(account_id, page, page_size)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return success(result)


@router.put("/{account_id}/opening-balance")
async def set_account_opening_balance(
    account_id: UUID,
    data: OpeningBalanceSet,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_OPENING_BALANCE_SET)),
):
    try:
        entry, before = await BankLedgerService(db, user).set_opening_balance(
            account_id, data.model_dump(), user.id,
        )
    except ValueError as exc:
        return error(40001, str(exc))
    after = {"entry_date": entry.entry_date.isoformat(), "amount": float(entry.amount)}
    await log_operation(
        db, user.id, user.real_name or user.username, "bank_ledger_entry", entry.id,
        "update" if before else "create",
        ip_address=request.client.host if request.client else None,
        before_data=before,
        after_data={"account_id": str(account_id), **after},
    )
    return success(after)


@router.post("/{account_id}/ledger-entries")
async def create_account_ledger_entry(
    account_id: UUID,
    data: BankLedgerEntryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_CREATE)),
):
    try:
        entry, created = await BankLedgerService(db, user).create_entry(
            account_id, data.model_dump(), user.id,
        )
    except ValueError as exc:
        return error(40001, str(exc))
    if created:
        await log_operation(
            db, user.id, user.real_name or user.username, "bank_ledger_entry", entry.id,
            "create",
            ip_address=request.client.host if request.client else None,
            after_data={
                "account_id": str(account_id),
                "entry_date": entry.entry_date.isoformat(),
                "direction": entry.direction,
                "amount": float(entry.amount),
                "summary": entry.summary,
                "category": entry.category,
                "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
                "order_id": str(entry.order_id) if entry.order_id else None,
            },
        )
    return success(BankLedgerService.entry_payload(entry))


@router.put("/{account_id}/ledger-entries/{entry_id}")
async def update_account_ledger_entry(
    account_id: UUID,
    entry_id: UUID,
    data: BankLedgerEntryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_CREATE)),
):
    try:
        service = BankLedgerService(db, user)
        entry, before = await service.update_entry(account_id, entry_id, data.model_dump())
    except ValueError as exc:
        return error(40001, str(exc))
    await log_operation(
        db, user.id, user.real_name or user.username, "bank_ledger_entry", entry.id,
        "update",
        ip_address=request.client.host if request.client else None,
        before_data=before,
        after_data=service.audit_snapshot(entry),
    )
    return success(BankLedgerService.entry_payload(entry))


@router.delete("/{account_id}/ledger-entries/{entry_id}")
async def delete_account_ledger_entry(
    account_id: UUID,
    entry_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(PERM_COMPANY_ACCOUNT_LEDGER_CREATE)),
):
    try:
        before = await BankLedgerService(db, user).delete_entry(account_id, entry_id)
    except ValueError as exc:
        return error(40001, str(exc))
    await log_operation(
        db, user.id, user.real_name or user.username, "bank_ledger_entry", entry_id,
        "delete",
        ip_address=request.client.host if request.client else None,
        before_data=before,
    )
    return success({"deleted": True})


@router.post("/{account_id}/project-cost-payments")
async def create_bank_project_cost(
    account_id: UUID,
    data: BankProjectCostCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_all_permissions(PERM_COMPANY_ACCOUNT_LEDGER_CREATE, "company_account:select", "expense:create")),
):
    try:
        async with db.begin_nested():
            cost, created = await BankLedgerService(db, user).create_project_cost(account_id, data.model_dump(), user.id)
    except ValueError as exc:
        return error(40001, str(exc))
    if created:
        await log_operation(
            db, user.id, user.real_name or user.username, "project_cost", UUID(cost["id"]),
            "create", ip_address=request.client.host if request.client else None,
            after_data={"cost_no": cost["cost_no"], "amount": cost["amount"], "payment_account_id": str(account_id)},
        )
    return success({"id": cost["id"], "cost_no": cost["cost_no"]})


@router.post("/{account_id}/customer-receipts")
async def create_bank_customer_receipt(
    account_id: UUID,
    data: BankCustomerReceiptCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_all_permissions(PERM_COMPANY_ACCOUNT_LEDGER_CREATE, "company_account:select", "payment:create")),
):
    try:
        async with db.begin_nested():
            receipt, created = await BankLedgerService(db, user).create_customer_receipt(account_id, data.model_dump(), user.id)
    except ValueError as exc:
        return error(40001, str(exc))
    if created:
        await log_operation(
            db, user.id, user.real_name or user.username, "payment", UUID(receipt["id"]),
            "create", ip_address=request.client.host if request.client else None,
            after_data={"payment_no": receipt["payment_no"], "amount": receipt["amount"], "payment_account_id": str(account_id)},
        )
    return success({"id": receipt["id"], "payment_no": receipt["payment_no"]})


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
