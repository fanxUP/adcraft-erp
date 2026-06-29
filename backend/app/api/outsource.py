from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, success_paginated, error
from app.schemas.outsource import VendorCreate, VendorUpdate, OutsourceTaskCreate, OutsourceTaskUpdate, OutsourcePaymentCreate
from app.services.outsource_service import OutsourceService

router = APIRouter(prefix="/outsource", tags=["Outsource"])


# ── Vendor ──

@router.get("/vendors")
async def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    service_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vendors, total = await service.list_vendors(page, page_size, keyword, service_type)
    return success_paginated(vendors, total, page, page_size)


@router.get("/vendors/{vendor_id}")
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vendor = await service.get_vendor(UUID(vendor_id))
    if not vendor:
        return error(40401, "外协商不存在")
    return success(vendor)


@router.post("/vendors")
async def create_vendor(
    data: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vendor = await service.create_vendor(data.model_dump())
    return success(vendor)


@router.put("/vendors/{vendor_id}")
async def update_vendor(
    vendor_id: str,
    data: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    try:
        vendor = await service.update_vendor(UUID(vendor_id), data.model_dump(exclude_none=True))
        return success(vendor)
    except ValueError as e:
        return error(40401, str(e))


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    ok = await service.delete_vendor(UUID(vendor_id))
    if not ok:
        return error(40401, "外协商不存在")
    return success(None)


# ── Task ──

@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    vendor_id: str | None = None,
    order_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vid = UUID(vendor_id) if vendor_id else None
    oid = UUID(order_id) if order_id else None
    tasks, total = await service.list_tasks(page, page_size, status, vid, oid)
    return success_paginated(tasks, total, page, page_size)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    task = await service.get_task(UUID(task_id))
    if not task:
        return error(40401, "外协任务不存在")
    return success(task)


@router.post("/tasks")
async def create_task(
    data: OutsourceTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    task = await service.create_task(data.model_dump())
    return success(task)


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: OutsourceTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    try:
        task = await service.update_task(UUID(task_id), data.model_dump(exclude_none=True))
        return success(task)
    except ValueError as e:
        return error(40401, str(e))


# ── Payment ──

@router.get("/payments")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor_id: str | None = None,
    task_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vid = UUID(vendor_id) if vendor_id else None
    tid = UUID(task_id) if task_id else None
    payments, total = await service.list_payments(page, page_size, vid, tid)
    return success_paginated(payments, total, page, page_size)


@router.post("/payments")
async def create_payment(
    data: OutsourcePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    payment = await service.create_payment(data.model_dump())
    return success(payment)
