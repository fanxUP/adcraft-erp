from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.order_repo import OrderRepository


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderRepository(db)

    async def list_orders(self, page: int, page_size: int, status: str | None = None, customer_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        orders, total = await self.repo.list_orders(skip=skip, limit=page_size, status=status, customer_id=customer_id)
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

    def _order_to_summary(self, o) -> dict:
        return {
            "id": str(o.id), "order_no": o.order_no,
            "customer_id": str(o.customer_id), "project_name": o.project_name,
            "status": o.status,
            "total_amount": float(o.total_amount),
            "paid_amount": float(o.paid_amount),
            "unpaid_amount": float(o.unpaid_amount),
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
