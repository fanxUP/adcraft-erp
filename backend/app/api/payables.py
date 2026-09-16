"""应付管理 API。

这里的付款只登记供应商/经营支出付款，不与客户收款 ``payments`` 表混用。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PERM_EXPENSE_READ, PERM_EXPENSE_UPDATE, require_permission
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.schemas.payment import PayablePaymentCreate, PayablePaymentVoid
from app.services.operation_log_service import log_operation, OBJ_EXPENSE, OBJ_PROJECT_COST
from app.services.payable_service import PayableService


router = APIRouter(prefix="/payables", tags=["Payables"])


def _object_type(source_type: str):
    return OBJ_PROJECT_COST if source_type == "project_cost" else OBJ_EXPENSE


@router.get("/")
async def list_payables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    supplier_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_EXPENSE_READ)),
):
    try:
        rows, total = await PayableService(db).list_payables(
            page,
            page_size,
            keyword,
            status,
            source_type,
            supplier_id,
        )
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}
    return success_paginated(rows, total, page, page_size)


@router.get("/{source_type}/{source_id}")
async def get_payable(
    source_type: str,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_EXPENSE_READ)),
):
    try:
        payable = await PayableService(db).get_payable(source_type, source_id)
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}
    if payable is None:
        return {"code": 40401, "message": "应付来源不存在或已删除", "data": None}
    return success(payable)


@router.post("/{source_type}/{source_id}/payments")
async def register_payable_payment(
    source_type: str,
    source_id: UUID,
    data: PayablePaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_EXPENSE_UPDATE)),
):
    try:
        payable = await PayableService(db).register_payment(
            source_type,
            source_id,
            data.model_dump(),
            current_user.id,
        )
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        _object_type(source_type),
        source_id,
        "payable_payment_create",
        ip_address=request.client.host if request.client else None,
        after_data={
            "source_type": source_type,
            "payment_amount": data.amount,
            "payment_method": data.payment_method,
        },
    )
    return success(payable)


@router.post("/{source_type}/{source_id}/payments/{payment_id}/void")
async def void_payable_payment(
    source_type: str,
    source_id: UUID,
    payment_id: UUID,
    data: PayablePaymentVoid,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_EXPENSE_UPDATE)),
):
    try:
        payable = await PayableService(db).void_payment(
            source_type,
            source_id,
            payment_id,
            data.void_reason,
        )
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        _object_type(source_type),
        source_id,
        "payable_payment_void",
        ip_address=request.client.host if request.client else None,
        after_data={"payment_id": str(payment_id), "void_reason": data.void_reason},
    )
    return success(payable)
