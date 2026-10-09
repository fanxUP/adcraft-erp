from datetime import date

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_FINANCE_VIEW_COST,
    PERM_OUTSOURCE_CENTER_READ,
    PERM_OUTSOURCE_PAYMENT_READ,
    PERM_OUTSOURCE_TASK_READ,
    PERM_OUTSOURCE_VENDOR_READ,
    PERM_EXPENSE_READ,
    PERM_EXPENSE_UPDATE,
    PERM_PAYMENT_READ,
    require_all_permissions,
    require_permission,
    user_has_permission,
)
from app.models.finance_reconciliation import FinancePaymentDateReconciliation
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.schemas.finance_reconciliation import (
    CostOverlapReviewWrite,
    PaymentDateReconciliationCreate,
    PaymentDateReconciliationVoid,
)
from app.services.finance_center_service import FinanceCenterService
from app.services.finance_reconciliation_service import FinanceReconciliationService
from app.services.operation_log_service import ACTION_CREATE, ACTION_UPDATE, log_operation


router = APIRouter(prefix="/finance-center", tags=["Finance Center"])


def _require_outsource_finance_access(current_user: User) -> None:
    required = (
        PERM_FINANCE_VIEW_COST,
        PERM_OUTSOURCE_CENTER_READ,
        PERM_OUTSOURCE_TASK_READ,
        PERM_OUTSOURCE_PAYMENT_READ,
        PERM_OUTSOURCE_VENDOR_READ,
    )
    if not all(user_has_permission(current_user, permission) for permission in required):
        raise HTTPException(status_code=403, detail="当前账号无权核对外协付款来源")


@router.get("/cashflow")
async def get_receipt_cashflow(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PAYMENT_READ)),
):
    try:
        result = await FinanceCenterService(db).receipt_summary(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(result)


@router.get("/cost-overlaps")
async def list_cost_overlap_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(
        PERM_FINANCE_VIEW_COST,
        PERM_OUTSOURCE_CENTER_READ,
        PERM_OUTSOURCE_TASK_READ,
        PERM_OUTSOURCE_VENDOR_READ,
    )),
):
    result = await FinanceCenterService(db).cost_overlap_candidates(page, page_size)
    return success_paginated(result["items"], result["total"], page, page_size)


@router.post("/payment-reconciliations")
async def create_payment_date_reconciliation(
    data: PaymentDateReconciliationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(PERM_EXPENSE_READ, PERM_EXPENSE_UPDATE)),
):
    if data.source_type in {"outsource_task", "outsource_payment"}:
        _require_outsource_finance_access(current_user)
    try:
        result = await FinanceReconciliationService(db).create_payment_date_reconciliation(
            **data.model_dump(),
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        "finance_payment_date_reconciliation",
        UUID(result["id"]),
        ACTION_CREATE,
        ip_address=request.client.host if request.client else None,
        after_data={
            "source_type": result["source_type"],
            "source_id": result["source_id"],
            "amount": result["amount"],
            "paid_at": result["paid_at"],
            "evidence_type": result["evidence_type"],
            "evidence_reference": result["evidence_reference"],
        },
    )
    return success(result)


@router.post("/payment-reconciliations/{reconciliation_id}/void")
async def void_payment_date_reconciliation(
    reconciliation_id: UUID,
    data: PaymentDateReconciliationVoid,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(PERM_EXPENSE_READ, PERM_EXPENSE_UPDATE)),
):
    record = await db.scalar(
        select(FinancePaymentDateReconciliation).where(
            FinancePaymentDateReconciliation.id == reconciliation_id
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="付款日期核对记录不存在")
    if record.source_type in {"outsource_task", "outsource_payment"}:
        _require_outsource_finance_access(current_user)
    try:
        result = await FinanceReconciliationService(db).void_payment_date_reconciliation(
            reconciliation_id=reconciliation_id,
            reason=data.reason,
            voided_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        "finance_payment_date_reconciliation",
        reconciliation_id,
        ACTION_UPDATE,
        ip_address=request.client.host if request.client else None,
        before_data={"source_type": record.source_type, "paid_at": record.paid_at.isoformat(), "amount": float(record.amount)},
        after_data={"voided_at": result["voided_at"], "void_reason": result["void_reason"]},
    )
    return success(result)


@router.post("/cost-overlaps/reviews")
async def review_cost_overlap(
    data: CostOverlapReviewWrite,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(
        PERM_FINANCE_VIEW_COST,
        PERM_EXPENSE_UPDATE,
        PERM_OUTSOURCE_CENTER_READ,
        PERM_OUTSOURCE_TASK_READ,
        PERM_OUTSOURCE_VENDOR_READ,
    )),
):
    try:
        result = await FinanceReconciliationService(db).review_cost_overlap(
            cost_id=data.cost_id,
            task_id=data.task_id,
            decision=data.decision,
            evidence_type=data.evidence_type,
            evidence_reference=data.evidence_reference,
            note=data.note,
            reviewed_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        "finance_cost_overlap_review",
        UUID(result["id"]),
        ACTION_UPDATE,
        ip_address=request.client.host if request.client else None,
        after_data={
            "cost_id": result["cost_id"],
            "task_id": result["task_id"],
            "decision": result["decision"],
            "evidence_type": result["evidence_type"],
            "evidence_reference": result["evidence_reference"],
            "note": result["note"],
        },
    )
    return success(result)
