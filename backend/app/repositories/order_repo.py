from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.order import Order, OrderItem, OrderStatusLog


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.db.execute(
            select(Order).where(Order.id == order_id, Order.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_orders(self, skip: int = 0, limit: int = 20, status: str | None = None,
                          customer_id: UUID | None = None, keyword: str | None = None) -> tuple[list[Order], int]:
        q = select(Order).where(Order.deleted_at.is_(None))
        if status:
            q = q.where(Order.status == status)
        if customer_id:
            q = q.where(Order.customer_id == customer_id)
        if keyword:
            q = q.where(
                Order.order_no.ilike(f"%{keyword}%") | Order.project_name.ilike(f"%{keyword}%")
            )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def update(self, order: Order, data: dict) -> Order:
        for k, v in data.items():
            if v is not None:
                setattr(order, k, v)
        await self.db.flush()
        return order

    async def get_status_logs(self, order_id: UUID) -> list[OrderStatusLog]:
        result = await self.db.execute(
            select(OrderStatusLog).where(OrderStatusLog.order_id == order_id).order_by(OrderStatusLog.operated_at.desc())
        )
        return list(result.scalars().all())

    async def create_status_log(self, order_id: UUID, from_status: str | None, to_status: str, reason: str | None, operated_by: UUID | None) -> OrderStatusLog:
        from datetime import datetime
        log = OrderStatusLog(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            operated_by=operated_by,
            operated_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log
