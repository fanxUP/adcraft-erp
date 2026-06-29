from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.order import OrderStatusChange
from app.schemas.common import success, success_paginated, error
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


class CostEntry(BaseModel):
    cost_amount: float


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    customer_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    cid = UUID(customer_id) if customer_id else None
    orders, total = await service.list_orders(page, page_size, status, cid)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.change_status(UUID(order_id), data.to_status, data.reason, current_user.id)
    return success(order)
