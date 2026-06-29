from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.order_repo import OrderRepository
from app.models.outsource import OutsourceTask
from app.models.inventory import StockRecord


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderRepository(db)

    async def list_orders(self, page: int, page_size: int, status: str | None = None,
                          customer_id: UUID | None = None, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        orders, total = await self.repo.list_orders(skip=skip, limit=page_size, status=status,
                                                     customer_id=customer_id, keyword=keyword)
        return [self._order_to_summary(o) for o in orders], total

    async def get_order(self, order_id: UUID) -> dict | None:
        order = await self.repo.get_by_id(order_id)
        if not order:
            return None
        return self._order_to_detail(order)

    async def change_status(self, order_id: UUID, to_status: str, reason: str | None, operated_by: UUID) -> dict:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("订单不存在")
        from_status = order.status
        await self.repo.update(order, {"status": to_status})
        await self.repo.create_status_log(order_id, from_status, to_status, reason, operated_by)
        return self._order_to_detail(order)

    async def set_cost(self, order_id: UUID, cost_amount: float) -> dict:
        """Set order cost and recalculate gross profit."""
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("订单不存在")
        cost = Decimal(str(cost_amount))
        total = Decimal(str(order.total_amount))
        gross_profit = total - cost
        await self.repo.update(order, {
            "cost_amount": float(cost),
            "gross_profit": float(gross_profit),
        })
        return self._order_to_detail(order)

    async def auto_calculate_cost(self, order_id: UUID) -> dict:
        """Auto-calculate order cost from outsource tasks + material stock-out records."""
        total_cost = Decimal("0")

        # Outsource costs
        result = await self.db.execute(
            select(func.coalesce(func.sum(OutsourceTask.total_amount), 0))
            .where(OutsourceTask.order_id == order_id, OutsourceTask.status == "settled")
        )
        total_cost += Decimal(str(result.scalar()))

        # Material costs
        result = await self.db.execute(
            select(func.coalesce(func.sum(StockRecord.total_cost), 0))
            .where(StockRecord.order_id == order_id, StockRecord.record_type == "out")
        )
        total_cost += Decimal(str(result.scalar()))

        return await self.set_cost(order_id, float(total_cost))

    def _order_to_summary(self, o) -> dict:
        return {
            "id": str(o.id), "order_no": o.order_no,
            "customer_id": str(o.customer_id), "project_name": o.project_name,
            "status": o.status,
            "total_amount": float(o.total_amount),
            "paid_amount": float(o.paid_amount),
            "unpaid_amount": float(o.unpaid_amount),
            "cost_amount": float(o.cost_amount),
            "gross_profit": float(o.gross_profit),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }

    def _order_to_detail(self, o) -> dict:
        return {
            "id": str(o.id), "order_no": o.order_no,
            "quote_id": str(o.quote_id) if o.quote_id else None,
            "customer_id": str(o.customer_id), "project_name": o.project_name,
            "sales_user_id": str(o.sales_user_id) if o.sales_user_id else None,
            "status": o.status,
            "total_amount": float(o.total_amount),
            "paid_amount": float(o.paid_amount),
            "unpaid_amount": float(o.unpaid_amount),
            "cost_amount": float(o.cost_amount),
            "gross_profit": float(o.gross_profit),
            "delivery_deadline": o.delivery_deadline.isoformat() if o.delivery_deadline else None,
            "installation_address": o.installation_address,
            "remark": o.remark,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": [
                {
                    "id": str(item.id), "item_name": item.item_name,
                    "product_id": str(item.product_id) if item.product_id else None,
                    "material_id": str(item.material_id) if item.material_id else None,
                    "process_id": str(item.process_id) if item.process_id else None,
                    "length": float(item.length) if item.length else None,
                    "width": float(item.width) if item.width else None,
                    "height": float(item.height) if item.height else None,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "unit_price": float(item.unit_price),
                    "subtotal_amount": float(item.subtotal_amount),
                    "remark": item.remark,
                }
                for item in (o.items or [])
            ],
            "status_logs": [
                {
                    "id": str(log.id),
                    "from_status": log.from_status,
                    "to_status": log.to_status,
                    "reason": log.reason,
                    "operated_by": str(log.operated_by) if log.operated_by else None,
                    "operated_at": log.operated_at.isoformat() if log.operated_at else None,
                }
                for log in (o.status_logs or [])
            ],
            "design_tasks": [
                {"id": str(t.id), "design_no": t.design_no, "status": t.status, "project_name": t.project_name}
                for t in (o.design_tasks or [])
            ],
            "production_tasks": [
                {"id": str(t.id), "production_no": t.production_no, "status": t.status, "project_name": t.project_name}
                for t in (o.production_tasks or [])
            ],
            "installation_tasks": [
                {"id": str(t.id), "installation_no": t.installation_no, "status": t.status, "project_name": t.project_name}
                for t in (o.installation_tasks or [])
            ],
        }
