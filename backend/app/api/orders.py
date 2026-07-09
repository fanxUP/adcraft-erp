from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.order import OrderStatusChange
from app.schemas.common import success, success_paginated, error
from app.services.order_service import OrderService
from app.services.operation_log_service import log_operation, OBJ_ORDER, ACTION_STATUS_CHANGE, ACTION_DELETE

router = APIRouter(prefix="/orders", tags=["Orders"])


class CostEntry(BaseModel):
    cost_amount: float


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=9999),
    status: str | None = None,
    customer_id: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    cid = UUID(customer_id) if customer_id else None
    orders, total = await service.list_orders(page, page_size, status, cid, keyword=keyword)
    return success_paginated(orders, total, page, page_size)


@router.get("/recycle/list")
async def list_deleted_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=9999),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = OrderService(db)
    orders, total = await service.list_deleted(page, page_size, keyword=keyword)
    return success_paginated(orders, total, page, page_size)


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.get_order(UUID(order_id))
    if not order:
        return {"code": 40401, "message": "订单不存在", "data": None}
    return success(order)


@router.post("/{order_id}/set-cost")
async def set_order_cost(
    order_id: str,
    data: CostEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    try:
        order = await service.set_cost(UUID(order_id), data.cost_amount)
        return success(order)
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/auto-cost")
async def auto_calculate_cost(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    try:
        order = await service.auto_calculate_cost(UUID(order_id))
        return success(order)
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/change-status")
async def change_order_status(
    order_id: str,
    data: OrderStatusChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    oid = UUID(order_id)
    order = await service.change_status(oid, data.to_status, data.reason, current_user.id)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_ORDER, oid, ACTION_STATUS_CHANGE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"status": data.to_status, "reason": data.reason})
    return success(order)


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = OrderService(db)
    oid = UUID(order_id)
    try:
        await service.delete_order(oid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_ORDER, oid, ACTION_DELETE,
                            ip_address=request.client.host if request.client else None)
        return success({"message": "订单已移入回收站"})
    except ValueError as e:
        return error(40001, str(e))


@router.post("/{order_id}/restore")
async def restore_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = OrderService(db)
    oid = UUID(order_id)
    try:
        order = await service.restore_order(oid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_ORDER, oid, "restore",
                            ip_address=request.client.host if request.client else None,
                            after_data={"status": "cancelled"})
        return success(order)
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/convert-to-quote")
async def convert_order_to_quote(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = OrderService(db)
    oid = UUID(order_id)
    try:
        quote = await service.convert_to_quote(oid, current_user.id)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_ORDER, oid, "convert_to_quote",
                            ip_address=request.client.host if request.client else None,
                            after_data={"quote_id": quote["id"]})
        return success(quote)
    except ValueError as e:
        return error(40001, str(e))
