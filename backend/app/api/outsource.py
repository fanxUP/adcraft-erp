from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.common import success, success_paginated, error
from app.schemas.outsource import VendorCreate, VendorUpdate, OutsourceTaskCreate, OutsourceTaskUpdate, OutsourcePaymentCreate
from app.services.outsource_service import OutsourceService
from app.services.operation_log_service import log_operation, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE, ACTION_STATUS_CHANGE
from app.services.operation_log_service import OBJ_OUTSOURCE_VENDOR, OBJ_OUTSOURCE_TASK, OBJ_OUTSOURCE_PAYMENT

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vendor = await service.create_vendor(data.model_dump())
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_OUTSOURCE_VENDOR, UUID(vendor["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"name": vendor["name"], "vendor_no": vendor["vendor_no"]})
    return success(vendor)


@router.put("/vendors/{vendor_id}")
async def update_vendor(
    vendor_id: str,
    data: VendorUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    vid = UUID(vendor_id)
    try:
        vendor = await service.update_vendor(vid, data.model_dump(exclude_none=True))
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_OUTSOURCE_VENDOR, vid, ACTION_UPDATE,
                            ip_address=request.client.host if request.client else None)
        return success(vendor)
    except ValueError as e:
        return error(40401, str(e))


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = OutsourceService(db)
    vid = UUID(vendor_id)
    ok = await service.delete_vendor(vid)
    if not ok:
        return error(40401, "外协商不存在")
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_OUTSOURCE_VENDOR, vid, ACTION_DELETE,
                        ip_address=request.client.host if request.client else None)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    task = await service.create_task(data.model_dump())
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_OUTSOURCE_TASK, UUID(task["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"task_no": task["task_no"], "vendor_id": task.get("vendor_id")})
    return success(task)


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: OutsourceTaskUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    tid = UUID(task_id)
    try:
        task = await service.update_task(tid, data.model_dump(exclude_none=True))
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_OUTSOURCE_TASK, tid, ACTION_UPDATE,
                            ip_address=request.client.host if request.client else None,
                            after_data={"status": task.get("status")})
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OutsourceService(db)
    payment = await service.create_payment(data.model_dump())
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_OUTSOURCE_PAYMENT, UUID(payment["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"payment_no": payment["payment_no"], "amount": payment["amount"]})
    return success(payment)


# ── Cancel Task (admin only) ──

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """取消外协任务。仅限管理员操作。"""
    service = OutsourceService(db)
    tid = UUID(task_id)
    try:
        task = await service.cancel_task(tid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_OUTSOURCE_TASK, tid, ACTION_STATUS_CHANGE,
                            ip_address=request.client.host if request.client else None,
                            after_data={"status": "cancelled"})
        return success(task)
    except ValueError as e:
        return error(40401, str(e))


# ── Revert Task (admin only: completed → in_progress) ──

@router.post("/tasks/{task_id}/revert")
async def revert_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """退回已完成的外协任务为进行中。仅限管理员操作。"""
    service = OutsourceService(db)
    tid = UUID(task_id)
    try:
        task = await service.revert_task(tid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_OUTSOURCE_TASK, tid, ACTION_STATUS_CHANGE,
                            ip_address=request.client.host if request.client else None,
                            after_data={"status": "in_progress"})
        return success(task)
    except ValueError as e:
        return error(40401, str(e))


# ── Delete Task (admin only: cancelled only) ──

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除已取消的外协任务。仅限管理员操作。"""
    service = OutsourceService(db)
    tid = UUID(task_id)
    try:
        ok = await service.delete_task(tid)
        if ok:
            await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                                OBJ_OUTSOURCE_TASK, tid, ACTION_DELETE,
                                ip_address=request.client.host if request.client else None)
            return success(None)
    except ValueError as e:
        return error(40401, str(e))


# ── Quote & Order dropdown data ──

@router.get("/quotes-for-dropdown")
async def list_quotes_for_dropdown(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回所有报价单供下拉选择（精简字段）"""
    from sqlalchemy import select
    from app.models.quote import Quote
    result = await db.execute(
        select(Quote.id, Quote.quote_no, Quote.project_name, Quote.customer_name)
        .where(Quote.deleted_at.is_(None))
        .order_by(Quote.created_at.desc())
    )
    rows = result.all()
    return success([
        {"id": str(r.id), "label": f"{r.quote_no} - {r.project_name}", "quote_no": r.quote_no, "project_name": r.project_name, "customer_name": r.customer_name}
        for r in rows
    ])


@router.get("/orders-for-dropdown")
async def list_orders_for_dropdown(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回所有订单供下拉选择（精简字段）"""
    from sqlalchemy import select
    from app.models.order import Order
    result = await db.execute(
        select(Order.id, Order.order_no, Order.project_name)
        .where(Order.deleted_at.is_(None))
        .order_by(Order.created_at.desc())
    )
    rows = result.all()
    return success([
        {"id": str(r.id), "label": f"{r.order_no} - {r.project_name}", "order_no": r.order_no, "project_name": r.project_name}
        for r in rows
    ])
