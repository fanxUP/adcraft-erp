from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.acceptance import AcceptanceForm, AcceptanceItem
from app.models.order import Order
from app.models.order import OrderItem
from app.repositories.acceptance_repo import AcceptanceRepository
from app.services.number_generator import generate_acceptance_no


class AcceptanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AcceptanceRepository(db)

    # ── 列表 ──────────────────────────────────────────────
    async def list_acceptances(self, page: int, page_size: int, **filters):
        items, total = await self.repo.list_all(page, page_size, **filters)
        return [self._to_list_dict(i) for i in items], total

    # ── 可用订单（未建验收单） ────────────────────────────
    async def list_available_orders(self) -> list[dict]:
        items = await self.repo.list_available_orders()
        return [
            {
                "id": str(o.id),
                "order_no": o.order_no,
                "customer_name": o.customer.name if o.customer else None,
                "project_name": o.project_name,
                "total_amount": float(o.total_amount),
                "status": o.status,
                "department": o.department,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in items
        ]

    # ── 可用报价单（未建验收单） ──────────────────────────
    async def list_available_quotes(self) -> list[dict]:
        items = await self.repo.list_available_quotes()
        return [
            {
                "id": str(q.id),
                "quote_no": q.quote_no,
                "customer_name": q.customer_name,
                "project_name": q.project_name,
                "total_amount": float(q.total_amount),
                "status": q.status,
                "department": q.department,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in items
        ]

    # ── 详情 ──────────────────────────────────────────────
    async def get_detail(self, acceptance_id: UUID):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        return self._to_detail_dict(form)

    # ── 创建 ──────────────────────────────────────────────
    async def create_acceptance(self, data: dict):
        order_id = UUID(data["order_id"]) if data.get("order_id") else None
        quote_id = UUID(data["quote_id"]) if data.get("quote_id") else None
        if order_id:
            data["order_id"] = order_id
        else:
            data.pop("order_id", None)
        if quote_id:
            data["quote_id"] = quote_id
        else:
            data.pop("quote_id", None)
        data["acceptance_no"] = await generate_acceptance_no(self.db)
        data["status"] = "draft"

        items_data = data.pop("items", [])
        if data.get("our_acceptor_id"):
            data["our_acceptor_id"] = UUID(data["our_acceptor_id"])

        form = await self.repo.create({**data, "items": items_data})

        # 未传入明细时，自动从订单/报价复制明细
        if not items_data:
            if order_id:
                await self._copy_order_items(form.id, order_id)
            elif quote_id:
                await self._copy_quote_items(form.id, quote_id)

        return self._to_detail_dict(await self.repo.get_by_id(form.id))

    async def _copy_order_items(self, acceptance_id: UUID, order_id: UUID) -> None:
        """Copy order items as acceptance items."""
        result = await self.db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        order = result.scalar_one_or_none()
        if not order or not order.items:
            return

        from app.services.order_service import _build_spec

        for oi in order.items:
            spec = _build_spec(oi)
            item = AcceptanceItem(
                acceptance_id=acceptance_id,
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

    async def _copy_quote_items(self, acceptance_id: UUID, quote_id: UUID) -> None:
        """Copy quote items as acceptance items."""
        from app.models.quote import Quote
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Quote).where(Quote.id == quote_id).options(selectinload(Quote.items))
        )
        quote = result.scalar_one_or_none()
        if not quote or not quote.items:
            return

        from app.services.order_service import _build_spec

        for qi in quote.items:
            spec = _build_spec(qi)
            item = AcceptanceItem(
                acceptance_id=acceptance_id,
                item_name=qi.item_name,
                material_process=qi.material_process,
                specification=spec,
                quantity=float(qi.quantity) if qi.quantity else None,
                unit=qi.unit,
                area=float(qi.area) if qi.area is not None else None,
                unit_price=float(qi.unit_price) if qi.unit_price is not None else None,
                subtotal=float(qi.subtotal_amount) if qi.subtotal_amount is not None else None,
                item_status="pending",
                group_name=qi.group_name,
                remark=qi.remark,
                image_url=qi.image_url,
            )
            self.db.add(item)

        await self.db.flush()

    # ── 更新 ──────────────────────────────────────────────
    async def update_acceptance(self, acceptance_id: UUID, data: dict):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        if form.status not in ("draft", "rejected"):
            raise ValueError("仅草稿和已驳回状态可编辑")

        if data.get("our_acceptor_id"):
            data["our_acceptor_id"] = UUID(data["our_acceptor_id"])
        elif "our_acceptor_id" in data and data["our_acceptor_id"] is None:
            data["our_acceptor_id"] = None  # allow clearing
        if "accepted_by" in data:
            data["accepted_by"] = data["accepted_by"]
        if "remark" in data:
            data["remark"] = data["remark"]

        items_data = data.pop("items", None)
        update_dict = {k: v for k, v in data.items() if k not in ("id", "acceptance_no", "order_id", "status")}
        if items_data is not None:
            update_dict["items"] = items_data

        form = await self.repo.update(form, update_dict)
        return self._to_detail_dict(form)

    # ── 删除 ──────────────────────────────────────────────
    async def delete_acceptance(self, acceptance_id: UUID):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        if form.status != "draft":
            raise ValueError("仅草稿状态可删除")
        await self.repo.soft_delete(form)

    # ── 状态变更 ──────────────────────────────────────────
    VALID_TRANSITIONS = {
        "draft": ["pending"],
        "pending": ["accepted", "rejected"],
        "rejected": ["draft"],
    }

    async def change_status(self, acceptance_id: UUID, to_status: str, **kwargs):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")

        allowed = self.VALID_TRANSITIONS.get(form.status, [])
        if to_status not in allowed:
            raise ValueError(f"不允许从 {form.status} 变更为 {to_status}")

        if to_status == "pending":
            if not form.items:
                raise ValueError("请先添加验收明细再提交")
            form.status = "pending"

        elif to_status == "accepted":
            form.status = "accepted"
            form.accepted_at = datetime.now()
            if kwargs.get("accepted_by"):
                form.accepted_by = kwargs["accepted_by"]

        elif to_status == "rejected":
            reason = kwargs.get("reason", "")
            if not reason:
                raise ValueError("驳回时请填写驳回原因")
            form.status = "rejected"
            form.reject_reason = reason

        elif to_status == "draft":
            form.status = "draft"
            form.reject_reason = None

        await self.db.flush()
        form = await self.repo.get_by_id(acceptance_id)
        return self._to_detail_dict(form)

    # ── 序列化 ──────────────────────────────────────────────
    def _to_list_dict(self, form: AcceptanceForm) -> dict:
        return {
            "id": str(form.id),
            "acceptance_no": form.acceptance_no,
            "order_id": str(form.order_id) if form.order_id else None,
            "order_no": form.order.order_no if form.order else (form.quote.quote_no if form.quote else None),
            "quote_id": str(form.quote_id) if form.quote_id else None,
            "quote_no": form.quote.quote_no if form.quote else None,
            "customer_name": (
                (form.order.customer.name if form.order.customer else None) if form.order
                else (form.quote.customer_name if form.quote else None)
            ),
            "project_name": (
                form.order.project_name if form.order
                else (form.quote.project_name if form.quote else None)
            ),
            "department": (
                form.order.department if form.order
                else (form.quote.department if form.quote else None)
            ),
            "total_amount": sum(
                float(i.subtotal or 0) for i in (form.items or [])
            ),
            "status": form.status,
            "accepted_at": form.accepted_at.isoformat() if form.accepted_at else None,
            "accepted_by": form.accepted_by,
            "created_at": form.created_at.isoformat() if form.created_at else None,
        }

    @staticmethod
    def _get_primary_contact(customer) -> str | None:
        if not customer or not customer.contacts:
            return None
        primary = next((c for c in customer.contacts if c.is_primary), None)
        return primary.name if primary else (customer.contacts[0].name if customer.contacts else None)
    def _to_detail_dict(self, form: AcceptanceForm) -> dict:
        # Resolve display fields: prefer order, fall back to quote
        _customer_name = (
            (form.order.customer.name if form.order.customer else None) if form.order
            else (form.quote.customer_name if form.quote else None)
        )
        _customer_phone = (
            form.order.customer.phone if form.order and form.order.customer
            else None
        )
        _customer_address = (
            form.order.customer.address if form.order and form.order.customer
            else None
        )
        _contact_person = (
            form.order.contact_person if form.order and form.order.contact_person
            else (self._get_primary_contact(form.order.customer) if form.order and form.order.customer
            else (form.quote.contact_person if form.quote else None))
        )
        _contact_phone = (
            form.order.contact_phone if form.order
            else (form.quote.contact_phone if form.quote else None)
        )
        _project_name = (
            form.order.project_name if form.order
            else (form.quote.project_name if form.quote else None)
        )
        _department = (
            form.order.department if form.order
            else (form.quote.department if form.quote else None)
        )

        return {
            "id": str(form.id),
            "acceptance_no": form.acceptance_no,
            "order_id": str(form.order_id) if form.order_id else None,
            "order_no": form.order.order_no if form.order else (form.quote.quote_no if form.quote else None),
            "quote_id": str(form.quote_id) if form.quote_id else None,
            "quote_no": form.quote.quote_no if form.quote else None,
            "customer_name": _customer_name,
            "customer_phone": _customer_phone,
            "customer_address": _customer_address,
            "contact_person": _contact_person,
            "contact_phone": _contact_phone,
            "order_date": form.order.created_at.isoformat() if form.order and form.order.created_at else None,
            "project_name": _project_name,
            "department": _department,
            "status": form.status,
            "accepted_at": form.accepted_at.isoformat() if form.accepted_at else None,
            "accepted_by": form.accepted_by,
            "our_acceptor_id": str(form.our_acceptor_id) if form.our_acceptor_id else None,
            "our_acceptor_name": form.our_acceptor.real_name if form.our_acceptor else None,
            "remark": form.remark,
            "reject_reason": form.reject_reason,
            "discount_amount": float(form.discount_amount),
            "advance_amount": float(form.advance_amount),
            "created_at": form.created_at.isoformat() if form.created_at else None,
            "updated_at": form.updated_at.isoformat() if form.updated_at else None,
            "items": [
                {
                    "id": str(item.id),
                    "acceptance_id": str(item.acceptance_id),
                    "order_item_id": str(item.order_item_id) if item.order_item_id else None,
                    "item_name": item.item_name,
                    "material_process": item.material_process,
                    "specification": item.specification,
                    "quantity": float(item.quantity) if item.quantity is not None else None,
                    "unit": item.unit,
                    "area": float(item.area) if item.area is not None else None,
                    "unit_price": float(item.unit_price) if item.unit_price is not None else None,
                    "subtotal": float(item.subtotal) if item.subtotal is not None else None,
                    "image_url": item.image_url,
                    "item_status": item.item_status,
                    "remark": item.remark,
                    "group_name": item.group_name,
                }
                for item in (form.items or [])
            ],
            "attachments": [
                {
                    "id": str(att.id),
                    "acceptance_id": str(att.acceptance_id),
                    "filename": att.filename,
                    "filepath": att.filepath,
                    "filesize": att.filesize,
                    "upload_by": str(att.upload_by) if att.upload_by else None,
                }
                for att in (form.attachments or [])
            ],
        }
