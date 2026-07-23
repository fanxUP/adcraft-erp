from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.common import success
from app.services.vehicle_dashboard_service import VehicleDashboardService

router = APIRouter(prefix="/vehicle-dashboard", tags=["Vehicle Dashboard"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """车辆管理首页：14 项核心指标"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_overview()
    return success(data)


@router.get("/today")
async def get_today_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """今日统计：派车、待收车、异常、费用"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_today_stats()
    return success(data)


@router.get("/monthly")
async def get_monthly_costs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """本月费用明细"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_monthly_costs()
    return success(data)


@router.get("/reminders")
async def get_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """保险、年检、驾驶证到期提醒"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_reminders()
    return success(data)


@router.get("/daily-report")
async def get_daily_report(
    date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """老板日报：车辆与安装运输部分"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_daily_report(date)
    return success(data)


@router.get("/expense-ranking")
async def get_expense_ranking(
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """单车费用排行"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_expense_ranking(year, month)
    return success(data)


@router.get("/driver-ranking")
async def get_driver_ranking(
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:read")),
):
    """司机出车排行"""
    service = VehicleDashboardService(db, current_user)
    data = await service.get_driver_ranking(year, month)
    return success(data)
