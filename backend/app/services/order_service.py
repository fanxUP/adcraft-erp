from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.order_repo import OrderRepository
from app.models.outsource import OutsourceTask
from app.models.inventory import StockRecord
from app.models.project_cost import ProjectCost


def _build_spec(item) -> str | None:
    """Build specification string from order/quote item dimensions + pieces."""
    parts = []
    if item.length:
        v = float(item.length)
        num = str(int(v)) if v == int(v) else str(v)
        parts.append(f"{num}{item.length_unit or 'm'}")
    if item.width:
        v = float(item.width)
        num = str(int(v)) if v == int(v) else str(v)
        parts.append(f"{num}{item.width_unit or 'm'}")
    if item.height:
        v = float(item.height)
        num = str(int(v)) if v == int(v) else str(v)
        parts.append(f"{num}{item.height_unit or 'm'}")
    if item.pieces and item.pieces > 1:
        parts.append(str(int(item.pieces)))
    return " × ".join(parts) if parts else None


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

    ORDER_TRANSITIONS = {
        "pending_confirm": ["confirmed", "cancelled"],
        "confirmed": ["in_progress", "cancelled"],
        "in_progress": ["in_production", "in_installation", "completed", "cancelled"],
        "in_production": ["in_installation", "completed", "cancelled"],
        "in_installation": ["completed", "cancelled"],
        "completed": ["cancelled"],
        "cancelled": [],
    }

    async def change_status(self, order_id: UUID, to_status: str, reason: str | None, operated_by: UUID) -> dict:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("订单不存在")
        from_status = order.status
        allowed = self.ORDER_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise ValueError(f"不允许从 {from_status} 流转到 {to_status}")
        await self.repo.update(order, {"status": to_status})
        await self.db.flush()
        await self.repo.create_status_log(order_id, from_status, to_status, reason, operated_by)

        # 订单完成时自动创建验收单
        if to_status == "completed":
            await self._auto_create_acceptance(order)

        # 订单取消时同步取消相关验收单
        if to_status == "cancelled":
            from app.models.acceptance import AcceptanceForm
            result = await self.db.execute(
                select(AcceptanceForm).where(
                    AcceptanceForm.order_id == order_id,
                    AcceptanceForm.deleted_at.is_(None),
                    AcceptanceForm.status != "cancelled",
                )
            )
            for af in result.scalars().all():
                af.status = "cancelled"

        # Send notification to sales user
        if order.sales_user_id and order.sales_user_id != operated_by:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            status_labels = {
                "pending_confirm": "待确认", "confirmed": "已确认", "in_progress": "进行中",
                "in_production": "生产中", "in_installation": "安装中", "completed": "已完成", "cancelled": "已取消",
            }
            from_label = status_labels.get(from_status, from_status)
            to_label = status_labels.get(to_status, to_status)
            await notif_svc.create_system_notification(
                user_id=order.sales_user_id,
                type_="order_status",
                title=f"订单状态变更: {order.order_no}",
                content=f"订单 {order.project_name} 状态从 {from_label} 变更为 {to_label}",
                link=f"/orders/{order_id}",
            )

        return self._order_to_detail(order)

    async def _auto_create_acceptance(self, order) -> None:
        """订单完成时自动创建验收单（如该订单尚无验收单）"""
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.services.number_generator import generate_acceptance_no

        existing = await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.order_id == order.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            return

        acceptance_no = await generate_acceptance_no(self.db)
        form = AcceptanceForm(
            acceptance_no=acceptance_no,
            order_id=order.id,
            status="draft",
        )
        self.db.add(form)
        await self.db.flush()

        for oi in order.items or []:
            spec = _build_spec(oi)

            item = AcceptanceItem(
                acceptance_id=form.id,
                order_item_id=oi.id,
                item_name=oi.item_name,
                material_process=oi.material_process,
                specification=spec,
                quantity=float(oi.quantity) if oi.quantity else None,
                unit=oi.unit,
                area=float(oi.area) if oi.area else None,
                unit_price=float(oi.unit_price) if oi.unit_price else None,
                subtotal=float(oi.subtotal_amount) if oi.subtotal_amount else None,
                item_status="pending",
                group_name=oi.group_name,
                remark=oi.remark,
                image_url=oi.image_url,
            )
            self.db.add(item)

        await self.db.flush()

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
        """Auto-calculate order cost from outsource tasks + material stock-out records + manual project costs."""
        total_cost = Decimal("0")

        # Outsource costs (settled + completed)
        result = await self.db.execute(
            select(func.coalesce(func.sum(OutsourceTask.total_amount), 0))
            .where(OutsourceTask.order_id == order_id, OutsourceTask.status.in_(["completed", "settled"]))
        )
        total_cost += Decimal(str(result.scalar()))

        # Material costs
        result = await self.db.execute(
            select(func.coalesce(func.sum(StockRecord.total_cost), 0))
            .where(StockRecord.order_id == order_id, StockRecord.record_type == "out")
        )
        total_cost += Decimal(str(result.scalar()))

        # Manual project costs
        result = await self.db.execute(
            select(func.coalesce(func.sum(ProjectCost.amount), 0))
            .where(ProjectCost.order_id == order_id, ProjectCost.deleted_at.is_(None))
        )
        total_cost += Decimal(str(result.scalar()))

        return await self.set_cost(order_id, float(total_cost))

    async def delete_order(self, order_id: UUID) -> None:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("订单不存在")
        if order.status != "cancelled":
            raise ValueError("只有已取消的订单可以删除")
        await self.repo.soft_delete(order)

    async def convert_to_quote(self, order_id: UUID, created_by: UUID) -> dict:
        """已取消订单转报价单，并删除原订单"""
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("订单不存在")
        if order.status != "cancelled":
            raise ValueError("只有已取消的订单可以转报价")

        # 创建报价单
        from app.services.quote_service import QuoteService
        from app.services.number_generator import generate_quote_no

        quote_svc = QuoteService(self.db)
        quote_no = await generate_quote_no(self.db)

        quote_data = {
            "quote_no": quote_no,
            "customer_id": str(order.customer_id) if order.customer_id else None,
            "customer_name": order.customer.name if order.customer else None,
            "project_name": order.project_name,
            "sales_user_id": str(order.sales_user_id) if order.sales_user_id else None,
            "status": "draft",
            "remark": f"由订单 {order.order_no} 转换",
            "items": []
        }

        # 复制订单明细
        for item in (order.items or []):
            quote_data["items"].append({
                "item_name": item.item_name,
                "product_id": str(item.product_id) if item.product_id else None,
                "material_id": str(item.material_id) if item.material_id else None,
                "process_id": str(item.process_id) if item.process_id else None,
                "length": float(item.length) if item.length else None,
                "length_unit": item.length_unit,
                "width": float(item.width) if item.width else None,
                "width_unit": item.width_unit,
                "height": float(item.height) if item.height else None,
                "height_unit": item.height_unit,
                "quantity": float(item.quantity),
                "unit": item.unit,
                "use_area": item.use_area,
                "quantity_mode": item.quantity_mode,
                "pieces": float(item.pieces) if item.pieces else None,
                "area": float(item.area) if item.area else None,
                "unit_price": float(item.unit_price),
                "process_fee": float(item.process_fee),
                "installation_fee": float(item.installation_fee),
                "design_fee": float(item.design_fee),
                "transport_fee": float(item.transport_fee),
                "other_fee": float(item.other_fee),
                "remark": item.remark,
                "image_url": item.image_url,
                "sort_order": item.sort_order,
                "group_name": item.group_name,
                "material_process": item.material_process,
            })

        quote = await quote_svc.create_quote(quote_data)

        # 删除原订单（软删除）
        await self.repo.soft_delete(order)

        return quote

    async def list_deleted(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        orders, total = await self.repo.list_deleted_orders(skip=skip, limit=page_size, keyword=keyword)
        return [self._order_to_summary(o) for o in orders], total

    async def restore_order(self, order_id: UUID) -> dict:
        order = await self.repo.get_deleted_by_id(order_id)
        if not order:
            raise ValueError("回收站中未找到该订单")
        await self.repo.restore(order)
        return self._order_to_detail(order)

    def _order_to_summary(self, o) -> dict:
        return {
            "id": str(o.id), "order_no": o.order_no,
            "customer_id": str(o.customer_id),
            "customer_name": o.customer.name if o.customer else None,
            "project_name": o.project_name,
            "department": o.department,
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
            "customer_id": str(o.customer_id),
            "customer_name": o.customer.name if o.customer else None,
            "project_name": o.project_name,
            "department": o.department,
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
                    "length_unit": item.length_unit,
                    "width": float(item.width) if item.width else None,
                    "width_unit": item.width_unit,
                    "height": float(item.height) if item.height else None,
                    "height_unit": item.height_unit,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "use_area": item.use_area,
                    "quantity_mode": item.quantity_mode,
                    "pieces": float(item.pieces) if item.pieces else None,
                    "specification": _build_spec(item),
                    "area": float(item.area) if item.area else None,
                    "unit_price": float(item.unit_price),
                    "process_fee": float(item.process_fee),
                    "installation_fee": float(item.installation_fee),
                    "design_fee": float(item.design_fee),
                    "transport_fee": float(item.transport_fee),
                    "other_fee": float(item.other_fee),
                    "subtotal_amount": float(item.subtotal_amount),
                    "remark": item.remark,
                    "sort_order": item.sort_order,
                    "group_name": item.group_name,
                    "material_process": item.material_process,
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
