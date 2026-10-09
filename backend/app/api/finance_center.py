from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_FINANCE_VIEW_COST,
    PERM_OUTSOURCE_CENTER_READ,
    PERM_OUTSOURCE_TASK_READ,
    PERM_OUTSOURCE_VENDOR_READ,
    PERM_PAYMENT_READ,
    require_all_permissions,
    require_permission,
)
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.services.finance_center_service import FinanceCenterService


router = APIRouter(prefix="/finance-center", tags=["Finance Center"])


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
