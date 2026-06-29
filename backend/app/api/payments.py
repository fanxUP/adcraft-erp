from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentVoid, StatementCreate, ExpenseCreate, ExpenseUpdate
from app.schemas.common import success, success_paginated
from app.services.payment_service import PaymentService, StatementService, ExpenseService
from app.services.operation_log_service import log_operation, OBJ_PAYMENT, OBJ_EXPENSE, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE

pay_router = APIRouter(prefix="/payments", tags=["Payments"])
stmt_router = APIRouter(prefix="/statements", tags=["Statements"])
exp_router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ── Payments ────────────────────────────────────────────────────────────────

@pay_router.get("/")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_id: str | None = None,
    customer_id: str | None = None,
    is_voided: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    oid = UUID(order_id) if order_id else None
    cid = UUID(customer_id) if customer_id else None
    payments, total = await service.list_payments(page, page_size, oid, cid, is_voided)
    return success_paginated(payments, total, page, page_size)


@pay_router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    payment = await service.get_payment(UUID(payment_id))
    if not payment:
        return {"code": 40401, "message": "收款记录不存在", "data": None}
    return success(payment)


@pay_router.post("/")
async def create_payment(
    data: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    payment = await service.create_payment(data.model_dump(), current_user.id)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_PAYMENT, UUID(payment["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"payment_no": payment["payment_no"], "amount": payment["amount"]})
    return success(payment)


@pay_router.post("/{payment_id}/void")
async def void_payment(
    payment_id: str,
    data: PaymentVoid,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    pid = UUID(payment_id)
    payment = await service.void_payment(pid, data.void_reason)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_PAYMENT, pid, "void",
                        ip_address=request.client.host if request.client else None,
                        after_data={"void_reason": data.void_reason})
    return success(payment)


@pay_router.post("/{payment_id}/upload-receipt")
async def upload_receipt(
    payment_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os, uuid as _uuid
    from datetime import datetime
    from sqlalchemy import update
    from app.core.config import settings
    from app.models.payment import Payment as PaymentModel

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    month_dir = datetime.utcnow().strftime("%Y%m")
    dest_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, month_dir)
    os.makedirs(dest_dir, exist_ok=True)
    stored_name = f"{_uuid.uuid4()}.{ext}"
    file_path = os.path.join(dest_dir, stored_name)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    await file.close()

    service = PaymentService(db)
    p = await service.repo.get_by_id(UUID(payment_id))
    if not p:
        return {"code": 40401, "message": "收款记录不存在", "data": None}
    rel_path = f"{month_dir}/{stored_name}"
    await db.execute(
        update(PaymentModel).where(PaymentModel.id == p.id).values(receipt_url=rel_path)
    )
    await db.flush()
    return success({"file_path": rel_path})


# ── Statements ──────────────────────────────────────────────────────────────

@stmt_router.get("/")
async def list_statements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StatementService(db)
    cid = UUID(customer_id) if customer_id else None
    stmts, total = await service.list_statements(page, page_size, cid)
    return success_paginated(stmts, total, page, page_size)


@stmt_router.get("/{statement_id}")
async def get_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StatementService(db)
    stmt = await service.get_statement(UUID(statement_id))
    if not stmt:
        return {"code": 40401, "message": "对账单不存在", "data": None}
    return success(stmt)


@stmt_router.post("/")
async def create_statement(
    data: StatementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StatementService(db)
    stmt = await service.create_statement(data.model_dump())
    return success(stmt)


@stmt_router.post("/{statement_id}/confirm")
async def confirm_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StatementService(db)
    stmt = await service.confirm_statement(UUID(statement_id), current_user.id)
    return success(stmt)


# ── Expenses ────────────────────────────────────────────────────────────────

@exp_router.get("/")
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    expenses, total = await service.list_expenses(page, page_size, category, start_date, end_date)
    return success_paginated(expenses, total, page, page_size)


@exp_router.get("/{expense_id}")
async def get_expense(
    expense_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    expense = await service.get_expense(UUID(expense_id))
    if not expense:
        return {"code": 40401, "message": "支出记录不存在", "data": None}
    return success(expense)


@exp_router.post("/")
async def create_expense(
    data: ExpenseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    expense = await service.create_expense(data.model_dump(), current_user.id)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_EXPENSE, UUID(expense["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"expense_no": expense["expense_no"], "amount": expense["amount"]})
    return success(expense)


@exp_router.put("/{expense_id}")
async def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    eid = UUID(expense_id)
    expense = await service.update_expense(eid, data.model_dump(exclude_none=True))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_EXPENSE, eid, ACTION_UPDATE,
                        ip_address=request.client.host if request.client else None)
    return success(expense)


@exp_router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    eid = UUID(expense_id)
    await service.delete_expense(eid)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_EXPENSE, eid, ACTION_DELETE,
                        ip_address=request.client.host if request.client else None)
    return success(None)
