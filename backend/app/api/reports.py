from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_CUSTOMER_READ,
    PERM_DASHBOARD_READ,
    PERM_ORDER_READ,
    PERM_OUTSOURCE_CENTER_READ,
    PERM_REPORT_READ,
    PERM_REPORT_VIEW_FINANCIAL,
    PERM_RESOURCE_CENTER_READ,
    PERM_TASK_COMPLETION_READ,
    PERM_TASK_QUEUE_READ,
    require_any_permission,
    require_permission,
)
from app.models.user import User
from app.schemas.common import success
from app.schemas.report import TaskCompletionKind, TaskCompletionPeriod, TaskCompletionType
from app.services.report_service import ReportService
from app.services.task_completion_metrics_service import (
    TaskCompletionAccessError,
    TaskCompletionEmployeeNotFound,
    TaskCompletionMetricsService,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(
        PERM_DASHBOARD_READ,
        PERM_TASK_QUEUE_READ,
        PERM_TASK_COMPLETION_READ,
        PERM_REPORT_READ,
        PERM_REPORT_VIEW_FINANCIAL,
        PERM_ORDER_READ,
        PERM_CUSTOMER_READ,
        PERM_RESOURCE_CENTER_READ,
        PERM_OUTSOURCE_CENTER_READ,
    )),
):
    service = ReportService(db, viewer=current_user)
    data = await service.get_dashboard()
    return success(data)


@router.get("/daily")
async def get_daily_report(
    date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(PERM_REPORT_READ, PERM_REPORT_VIEW_FINANCIAL)),
):
    service = ReportService(db, viewer=current_user)
    data = await service.get_daily_report(date)
    return success(data)


@router.get("/monthly")
async def get_monthly_report(
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(PERM_REPORT_READ, PERM_REPORT_VIEW_FINANCIAL)),
):
    service = ReportService(db, viewer=current_user)
    data = await service.get_monthly_report(year, month)
    return success(data)


@router.get("/customer-debt")
async def get_customer_debt(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_REPORT_VIEW_FINANCIAL)),
):
    service = ReportService(db, viewer=current_user)
    data = await service.get_customer_debt()
    return success(data)


@router.get("/task-completion/summary")
async def get_task_completion_summary(
    period: TaskCompletionPeriod = Query("month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_TASK_COMPLETION_READ)),
):
    """Return non-financial completion KPIs for the operating cockpit."""
    service = TaskCompletionMetricsService(db, viewer=current_user)
    try:
        data = await service.get_summary(period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return success(data)


@router.get("/task-completion/details")
async def get_task_completion_details(
    period: TaskCompletionPeriod = Query("month"),
    kind: TaskCompletionKind = Query("detail"),
    employee_id: UUID | None = Query(None),
    task_type: TaskCompletionType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_TASK_COMPLETION_READ)),
):
    """Return server-paginated completion rows without commercial fields."""
    service = TaskCompletionMetricsService(db, viewer=current_user)
    try:
        data = await service.get_details(
            period=period,
            kind=kind,
            employee_id=employee_id,
            task_type=task_type,
            page=page,
            page_size=page_size,
        )
    except TaskCompletionAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TaskCompletionEmployeeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return success(data)
