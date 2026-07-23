import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    require_permission,
    PERM_VEHICLE_READ, PERM_VEHICLE_CREATE, PERM_VEHICLE_UPDATE,
    PERM_FINANCE_REVIEW,
)
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.vehicle_use_request import VehicleUseRequestCreate, VehicleUseRequestUpdate, VehicleUseRequestReject
from app.schemas.vehicle_dispatch import VehicleDispatchCreate, VehicleDispatchUpdate
from app.schemas.vehicle_trip import DispatchStart, DispatchArrive, DispatchReturn
from app.schemas.vehicle_expense import (
    FuelRecordCreate, FuelRecordUpdate, FuelRecordReview,
    MaintenanceRecordCreate, MaintenanceRecordUpdate, MaintenanceRecordReview,
    CostAllocationCreate,
    CertificateCreate, CertificateUpdate,
    IncidentCreate, IncidentUpdate, IncidentResolve,
)
from app.schemas.common import success, success_paginated
from app.services.vehicle_service import VehicleService
from app.services.vehicle_report_service import VehicleReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
driver_router = APIRouter(prefix="/vehicle-drivers", tags=["Vehicle Drivers"])
request_router = APIRouter(prefix="/vehicle-use-requests", tags=["Vehicle Use Requests"])
dispatch_router = APIRouter(prefix="/vehicle-dispatches", tags=["Vehicle Dispatches"])
trip_router = APIRouter(prefix="/vehicle-trip-records", tags=["Vehicle Trip Records"])


def _get_service(db: AsyncSession, current_user: User, request: Request) -> VehicleService:
    ip = request.client.host if request.client else None
    return VehicleService(db, current_user, ip)


# ── 车辆档案 ──────────────────────────────────────────────────────────────────

@router.get("/available")
async def list_available_vehicles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vehicles, _ = await service.list_vehicles(1, 100, status="available")
    return success(vehicles)


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
    current_user: User = Depends(require_permission(PERM_VEHICLE_CREATE)),
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
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.update_vehicle(UUID(vehicle_id), data.model_dump(exclude_none=True))
    return success(vehicle)


@router.post("/{vehicle_id}/disable")
async def disable_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.disable_vehicle(UUID(vehicle_id))
    return success(vehicle)


@router.post("/{vehicle_id}/enable")
async def enable_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.enable_vehicle(UUID(vehicle_id))
    return success(vehicle)


@router.post("/{vehicle_id}/scrap")
async def scrap_vehicle(
    vehicle_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    vehicle = await service.scrap_vehicle(UUID(vehicle_id))
    return success(vehicle)


# ── 司机档案 ──────────────────────────────────────────────────────────────────

@driver_router.get("/available")
async def list_available_drivers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    drivers, _ = await service.list_drivers(1, 100, status="active")
    return success(drivers)


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
    current_user: User = Depends(require_permission(PERM_VEHICLE_CREATE)),
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
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    driver = await service.update_driver(UUID(driver_id), data)
    return success(driver)


@driver_router.post("/{driver_id}/disable")
async def disable_driver(
    driver_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    driver = await service.disable_driver(UUID(driver_id))
    return success(driver)


@driver_router.post("/{driver_id}/enable")
async def enable_driver(
    driver_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    driver = await service.enable_driver(UUID(driver_id))
    return success(driver)


# ── 用车申请 ──────────────────────────────────────────────────────────────────

@request_router.get("/")
async def list_requests(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    requester_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    rid = UUID(requester_id) if requester_id else None
    requests, total = await service.list_requests(page, page_size, keyword, status, rid)
    return success_paginated(requests, total, page, page_size)


@request_router.post("/")
async def create_request(
    data: VehicleUseRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    req = await service.create_request(data.model_dump(exclude_none=True))
    return success(req)


@request_router.get("/{request_id}")
async def get_request(
    request_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    req = await service.get_request(UUID(request_id))
    if not req:
        return {"code": 40401, "message": "用车申请不存在", "data": None}
    return success(req)


@request_router.patch("/{request_id}")
async def update_request(
    request_id: str,
    data: VehicleUseRequestUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    req = await service.update_request(UUID(request_id), data.model_dump(exclude_none=True))
    return success(req)


@request_router.post("/{request_id}/submit")
async def submit_request(
    request_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    req = await service.submit_request(UUID(request_id))
    return success(req)


@request_router.post("/{request_id}/approve")
async def approve_request(
    request_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    req = await service.approve_request(UUID(request_id))
    return success(req)


@request_router.post("/{request_id}/reject")
async def reject_request(
    request_id: str,
    data: VehicleUseRequestReject,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    req = await service.reject_request(UUID(request_id), data.reject_reason)
    return success(req)


@request_router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    req = await service.cancel_request(UUID(request_id))
    return success(req)


# ── 派车管理 ──────────────────────────────────────────────────────────────────

@dispatch_router.get("/")
async def list_dispatches(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    did = UUID(driver_id) if driver_id else None
    dispatches, total = await service.list_dispatches(page, page_size, keyword, status, vid, did)
    return success_paginated(dispatches, total, page, page_size)


@dispatch_router.post("/")
async def create_dispatch(
    data: VehicleDispatchCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    d = await service.create_dispatch(data.model_dump(exclude_none=True))
    return success(d)


@dispatch_router.get("/{dispatch_id}")
async def get_dispatch(
    dispatch_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    d = await service.get_dispatch(UUID(dispatch_id))
    if not d:
        return {"code": 40401, "message": "派车单不存在", "data": None}
    return success(d)


@dispatch_router.patch("/{dispatch_id}")
async def update_dispatch(
    dispatch_id: str,
    data: VehicleDispatchUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    d = await service.update_dispatch(UUID(dispatch_id), data.model_dump(exclude_none=True))
    return success(d)


@dispatch_router.post("/{dispatch_id}/cancel")
async def cancel_dispatch(
    dispatch_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    d = await service.cancel_dispatch(UUID(dispatch_id))
    return success(d)


@dispatch_router.post("/{dispatch_id}/start")
async def start_dispatch(
    dispatch_id: str,
    data: DispatchStart,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    d = await service.start_dispatch(UUID(dispatch_id), data.model_dump(exclude_none=True))
    return success(d)


@dispatch_router.post("/{dispatch_id}/arrive")
async def arrive_dispatch(
    dispatch_id: str,
    data: DispatchArrive,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    d = await service.arrive_dispatch(UUID(dispatch_id), data.model_dump(exclude_none=True))
    return success(d)


@dispatch_router.post("/{dispatch_id}/finish")
async def finish_dispatch(
    dispatch_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    d = await service.finish_dispatch(UUID(dispatch_id), {})
    return success(d)


@dispatch_router.post("/{dispatch_id}/return")
async def return_dispatch(
    dispatch_id: str,
    data: DispatchReturn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    d = await service.return_dispatch(UUID(dispatch_id), data.model_dump(exclude_none=True))
    return success(d)


# ── 出车/收车台账 ──────────────────────────────────────────────────────────

@trip_router.get("/")
async def list_trip_records(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    did = UUID(driver_id) if driver_id else None
    records, total = await service.list_trip_records(page, page_size, vid, did)
    return success_paginated(records, total, page, page_size)


@trip_router.get("/{trip_id}")
async def get_trip_record(
    trip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_trip_record(UUID(trip_id))
    if not r:
        return {"code": 40401, "message": "台账记录不存在", "data": None}
    return success(r)


# ── 油费记录 ──────────────────────────────────────────────────────────────────

fuel_router = APIRouter(prefix="/vehicle-fuel-records", tags=["Vehicle Fuel Records"])


@fuel_router.get("/")
async def list_fuel_records(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    did = UUID(driver_id) if driver_id else None
    records, total = await service.list_fuel_records(page, page_size, vid, did, status)
    return success_paginated(records, total, page, page_size)


@fuel_router.post("/")
async def create_fuel_record(
    data: FuelRecordCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.create_fuel_record(data.model_dump(exclude_none=True))
    return success(r)


@fuel_router.get("/{record_id}")
async def get_fuel_record(
    record_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_fuel_record(UUID(record_id))
    if not r:
        return {"code": 40401, "message": "油费记录不存在", "data": None}
    return success(r)


@fuel_router.patch("/{record_id}")
async def update_fuel_record(
    record_id: str,
    data: FuelRecordUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.update_fuel_record(UUID(record_id), data.model_dump(exclude_none=True))
    return success(r)


@fuel_router.post("/{record_id}/review")
async def review_fuel_record(
    record_id: str,
    data: FuelRecordReview,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_REVIEW)),
):
    service = _get_service(db, current_user, request)
    r = await service.review_fuel_record(UUID(record_id), data.status, data.remark)
    return success(r)


# ── 维修保养记录 ──────────────────────────────────────────────────────────────

maintenance_router = APIRouter(prefix="/vehicle-maintenance-records", tags=["Vehicle Maintenance Records"])


@maintenance_router.get("/")
async def list_maintenance_records(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    maintenance_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    records, total = await service.list_maintenance_records(page, page_size, vid, maintenance_type, status)
    return success_paginated(records, total, page, page_size)


@maintenance_router.post("/")
async def create_maintenance_record(
    data: MaintenanceRecordCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.create_maintenance_record(data.model_dump(exclude_none=True))
    return success(r)


@maintenance_router.get("/{record_id}")
async def get_maintenance_record(
    record_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_maintenance_record(UUID(record_id))
    if not r:
        return {"code": 40401, "message": "维修保养记录不存在", "data": None}
    return success(r)


@maintenance_router.patch("/{record_id}")
async def update_maintenance_record(
    record_id: str,
    data: MaintenanceRecordUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.update_maintenance_record(UUID(record_id), data.model_dump(exclude_none=True))
    return success(r)


@maintenance_router.post("/{record_id}/review")
async def review_maintenance_record(
    record_id: str,
    data: MaintenanceRecordReview,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_FINANCE_REVIEW)),
):
    service = _get_service(db, current_user, request)
    r = await service.review_maintenance_record(UUID(record_id), data.status, data.remark)
    return success(r)


# ── 通用费用 ──────────────────────────────────────────────────────────────────

cost_router = APIRouter(prefix="/vehicle-cost-records", tags=["Vehicle Cost Records"])


@cost_router.get("/")
async def list_cost_allocations(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    cost_type: str | None = None,
    source_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    records, total = await service.list_cost_allocations(page, page_size, vid, cost_type, source_type)
    return success_paginated(records, total, page, page_size)


@cost_router.post("/")
async def create_cost_allocation(
    data: CostAllocationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.create_cost_allocation(data.model_dump(exclude_none=True))
    return success(r)


@cost_router.get("/{cost_id}")
async def get_cost_allocation(
    cost_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_cost_allocation(UUID(cost_id))
    if not r:
        return {"code": 40401, "message": "费用记录不存在", "data": None}
    return success(r)


# ── 保险/年检/证件 ──────────────────────────────────────────────────────────

certificate_router = APIRouter(prefix="/vehicle-certificates", tags=["Vehicle Certificates"])


@certificate_router.get("/")
async def list_certificates(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    certificate_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    records, total = await service.list_certificates(page, page_size, vid, certificate_type, status)
    return success_paginated(records, total, page, page_size)


@certificate_router.get("/expiring")
async def list_expiring_certificates(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    vehicle_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    records = await service.list_expiring_certificates(days, vid)
    return success(records)


@certificate_router.post("/")
async def create_certificate(
    data: CertificateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    r = await service.create_certificate(data.model_dump(exclude_none=True))
    return success(r)


@certificate_router.get("/{cert_id}")
async def get_certificate(
    cert_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_certificate(UUID(cert_id))
    if not r:
        return {"code": 40401, "message": "证件记录不存在", "data": None}
    return success(r)


@certificate_router.patch("/{cert_id}")
async def update_certificate(
    cert_id: str,
    data: CertificateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    r = await service.update_certificate(UUID(cert_id), data.model_dump(exclude_none=True))
    return success(r)


@certificate_router.delete("/{cert_id}")
async def delete_certificate(
    cert_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    await service.delete_certificate(UUID(cert_id))
    return success(None)


# ── 违章/事故/异常 ──────────────────────────────────────────────────────────

incident_router = APIRouter(prefix="/vehicle-incidents", tags=["Vehicle Incidents"])


@incident_router.get("/")
async def list_incidents(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: str | None = None,
    incident_type: str | None = None,
    status: str | None = None,
    driver_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    vid = UUID(vehicle_id) if vehicle_id else None
    did = UUID(driver_id) if driver_id else None
    records, total = await service.list_incidents(page, page_size, vid, incident_type, status, did)
    return success_paginated(records, total, page, page_size)


@incident_router.post("/")
async def create_incident(
    data: IncidentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.create_incident(data.model_dump(exclude_none=True))
    return success(r)


@incident_router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user, request)
    r = await service.get_incident(UUID(incident_id))
    if not r:
        return {"code": 40401, "message": "异常记录不存在", "data": None}
    return success(r)


@incident_router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    data: IncidentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    r = await service.update_incident(UUID(incident_id), data.model_dump(exclude_none=True))
    return success(r)


@incident_router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    data: IncidentResolve,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    r = await service.resolve_incident(UUID(incident_id), data.resolution, data.status)
    return success(r)


@incident_router.delete("/{incident_id}")
async def delete_incident(
    incident_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    service = _get_service(db, current_user, request)
    await service.delete_incident(UUID(incident_id))
    return success(None)


# ── 车辆报表 ──────────────────────────────────────────────────────────────────

report_router = APIRouter(prefix="/vehicle-reports", tags=["Vehicle Reports"])


@report_router.get("/overview")
async def get_report_overview(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_overview(year, month)
    return success(data)


@report_router.get("/costs")
async def get_costs_by_vehicle(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_costs_by_vehicle(year, month, start_date, end_date)
    return success(data)


@report_router.get("/drivers")
async def get_costs_by_driver(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_costs_by_driver(year, month, start_date, end_date)
    return success(data)


@report_router.get("/mileage")
async def get_mileage_stats(
    request: Request,
    year: int | None = None,
    vehicle_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    vid = UUID(vehicle_id) if vehicle_id else None
    data = await svc.get_mileage_stats(year, vid)
    return success(data)


@report_router.get("/dispatches")
async def get_dispatch_stats(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_dispatch_stats(year, month, start_date, end_date)
    return success(data)


@report_router.get("/order-costs")
async def get_order_costs(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_order_costs(year, month, start_date, end_date)
    return success(data)


@report_router.get("/cost-types")
async def get_cost_by_type(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):

    svc = VehicleReportService(db, current_user)
    data = await svc.get_cost_by_type(year, month, start_date, end_date)
    return success(data)
