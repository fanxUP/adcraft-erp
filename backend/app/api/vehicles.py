import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.common import success, success_paginated
from app.services.vehicle_service import VehicleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
driver_router = APIRouter(prefix="/vehicle-drivers", tags=["Vehicle Drivers"])


def _get_service(db: AsyncSession, current_user: User, request: Request) -> VehicleService:
    ip = request.client.host if request.client else None
    return VehicleService(db, current_user, ip)


# ── 车辆档案 ──────────────────────────────────────────────────────────────────

@router.get("/")
async def list_vehicles(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    vehicle_type: str | None = None,
    status: str | None = None,
    driver_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    did = UUID(driver_id) if driver_id else None
    vehicles, total = await service.list_vehicles(page, page_size, keyword, vehicle_type, status, did)
    return success_paginated(vehicles, total, page, page_size)


@router.post("/")
async def create_vehicle(
    data: VehicleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:create")),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.create_vehicle(data.model_dump(exclude_none=True))
    return success(vehicle)


@router.get("/{vehicle_id}")
async def get_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.get_vehicle(UUID(vehicle_id))
    if not vehicle:
        return {"code": 40401, "message": "车辆不存在", "data": None}
    return success(vehicle)


@router.patch("/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    data: VehicleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.update_vehicle(UUID(vehicle_id), data.model_dump(exclude_none=True))
    return success(vehicle)


@router.post("/{vehicle_id}/disable")
async def disable_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.disable_vehicle(UUID(vehicle_id))
    return success(vehicle)


@router.post("/{vehicle_id}/enable")
async def enable_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.enable_vehicle(UUID(vehicle_id))
    return success(vehicle)


@router.post("/{vehicle_id}/scrap")
async def scrap_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.scrap_vehicle(UUID(vehicle_id))
    return success(vehicle)


# ── 司机档案 ──────────────────────────────────────────────────────────────────

@driver_router.get("/")
async def list_drivers(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    drivers, total = await service.list_drivers(page, page_size, keyword, status)
    return success_paginated(drivers, total, page, page_size)


@driver_router.post("/")
async def create_driver(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:create")),
):
    service = _get_service(db, current_user, request)
    driver = await service.create_driver(data)
    return success(driver)


@driver_router.get("/{driver_id}")
async def get_driver(
    driver_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    driver = await service.get_driver(UUID(driver_id))
    if not driver:
        return {"code": 40401, "message": "司机不存在", "data": None}
    return success(driver)


@driver_router.patch("/{driver_id}")
async def update_driver(
    driver_id: str,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    driver = await service.update_driver(UUID(driver_id), data)
    return success(driver)


@driver_router.post("/{driver_id}/disable")
async def disable_driver(
    driver_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    driver = await service.disable_driver(UUID(driver_id))
    return success(driver)


@driver_router.post("/{driver_id}/enable")
async def enable_driver(
    driver_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vehicle:update")),
):
    service = _get_service(db, current_user, request)
    driver = await service.enable_driver(UUID(driver_id))
    return success(driver)
