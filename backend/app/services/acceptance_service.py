from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.acceptance import AcceptanceForm, AcceptanceItem
from app.models.business_document import BusinessDocument
from app.repositories.acceptance_repo import AcceptanceRepository
from app.services.number_generator import generate_acceptance_no
from app.services.business_document_service import _build_spec, BusinessDocumentService


class AcceptanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AcceptanceRepository(db)

    # ── 列表 ──────────────────────────────────────────────
    async def list_acceptances(self, page: int, page_size: int, **filters):
        items, total = await self.repo.list_all(page, page_size, **filters)
        return [self._to_list_dict(i) for i in items], total

    # ── 可用订单 ──
    async def list_available_orders(self) -> list[dict]:
        items = await self.repo.list_available_orders()
        result = []
        for d in items:
            item = BusinessDocumentService._to_ref(d)
            item["created_at"] = d.created_at.isoformat() if d.created_at else None
            result.append(item)
        return result

    # ── 可用报价 ──
    async def list_available_quotes(self) -> list[dict]:
        items = await self.repo.list_available_quotes()
        result = []
        for d in items:
            item = BusinessDocumentService._to_ref(d)
            item["created_at"] = d.created_at.isoformat() if d.created_at else None
            result.append(item)
        return result

    # ── 详情 ──
    async def get_detail(self, acceptance_id: UUID):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        return self._to_detail_dict(form)

    # ── 创建 ──
    async def create_acceptance(self, data: dict):
        doc_id = UUID(data["document_id"]) if data.get("document_id") else None
        # backward compat: accept order_id or quote_id
        if not doc_id:
            if data.get("order_id"):
                doc_id = UUID(data["order_id"])
            elif data.get("quote_id"):
                doc_id = UUID(data["quote_id"])

        data["document_id"] = doc_id
        data.pop("order_id", None)
        data.pop("quote_id", None)
        data["acceptance_no"] = await generate_acceptance_no(self.db)
        data["status"] = "draft"

        items_data = data.pop("items", [])
        if data.get("our_acceptor_id"):
            data["our_acceptor_id"] = UUID(data["our_acceptor_id"])

        form = await self.repo.create({**data, "items": items_data})

        # 未传入明细时，自动从单据复制明细
        if not items_data and doc_id:
            await self._copy_doc_items(form.id, doc_id)

        return self._to_detail_dict(await self.repo.get_by_id(form.id))

    async def _copy_doc_items(self, acceptance_id: UUID, doc_id: UUID) -> None:
        """统一从 business_document 复制明细（取代 _copy_order_items + _copy_quote_items）。"""
        result = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id == doc_id)
            .options(selectinload(BusinessDocument.items))
        )
        doc = result.scalar_one_or_none()
        if not doc or not doc.items:
            return

        for item in doc.items:
            spec = _build_spec(item)
            ai = AcceptanceItem(
                acceptance_id=acceptance_id,
                document_item_id=item.id,
                item_name=item.item_name,
                material_process=item.material_process,
                specification=spec,
                quantity=float(item.quantity) if item.quantity else None,
                unit=item.unit,
                area=float(item.area) if item.area else None,
                unit_price=float(item.unit_price) if item.unit_price else None,
                subtotal=float(item.subtotal_amount) if item.subtotal_amount else None,
                item_status="pending",
                group_name=item.group_name,
                remark=item.remark,
                image_url=item.image_url,
            )
            self.db.add(ai)

        await self.db.flush()

    # ── 更新 ──
    async def update_acceptance(self, acceptance_id: UUID, data: dict):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        if form.status not in ("draft", "rejected"):
            raise ValueError("仅草稿和已驳回状态可编辑")

        if data.get("our_acceptor_id"):
            data["our_acceptor_id"] = UUID(data["our_acceptor_id"])
        elif "our_acceptor_id" in data and data["our_acceptor_id"] is None:
            data["our_acceptor_id"] = None

        items_data = data.pop("items", None)
        update_dict = {k: v for k, v in data.items()
                       if k not in ("id", "acceptance_no", "document_id", "status")}
        if items_data is not None:
            update_dict["items"] = items_data

        form = await self.repo.update(form, update_dict)
        return self._to_detail_dict(form)

    # ── 删除 ──
    async def delete_acceptance(self, acceptance_id: UUID):
        form = await self.repo.get_by_id(acceptance_id)
        if not form:
            raise ValueError("验收单不存在")
        if form.status != "draft":
            raise ValueError("仅草稿状态可删除")
        await self.repo.soft_delete(form)

    # ── 状态变更 ──
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

    # ── 序列化（统一访问 form.document） ──
    @staticmethod
    def _doc_info(form: AcceptanceForm):
        """从统一 document 关系中提取显示信息。"""
        d = form.document
        if not d:
            return {
                "source_type": "独立",
                "doc_no": None,
                "doc_type": None,
                "customer_name": None,
                "customer_phone": None,
                "customer_address": None,
                "contact_person": None,
                "contact_phone": None,
                "project_name": None,
                "department": None,
                "order_date": None,
            }
        is_order = d.doc_type == "order"
        return {
            "source_type": "订单" if is_order else "报价",
            "doc_no": d.doc_no,
            "doc_type": d.doc_type,
            "customer_name": (
                d.customer.name if (is_order and d.customer) else (d.customer_name or None)
            ),
            "customer_phone": d.customer.phone if (is_order and d.customer) else None,
            "customer_address": d.customer.address if (is_order and d.customer) else None,
            "contact_person": d.contact_person or (
                AcceptanceService._primary_contact(d.customer) if (is_order and d.customer) else None
            ),
            "contact_phone": d.contact_phone,
            "project_name": d.project_name,
            "department": d.department,
            "order_date": d.created_at.isoformat() if (is_order and d.created_at) else None,
        }

    @staticmethod
    def _primary_contact(customer) -> str | None:
        if not customer or not customer.contacts:
            return None
        primary = next((c for c in customer.contacts if c.is_primary), None)
        return primary.name if primary else (customer.contacts[0].name if customer.contacts else None)

    def _to_list_dict(self, form: AcceptanceForm) -> dict:
        info = self._doc_info(form)
        return {
            "id": str(form.id),
            "acceptance_no": form.acceptance_no,
            "document_id": str(form.document_id) if form.document_id else None,
            # Backward-compat aliases
            "order_id": str(form.document_id) if (info["doc_type"] == "order") else None,
            "quote_id": str(form.document_id) if (info["doc_type"] == "quote") else None,
            "order_no": info["doc_no"] if info["doc_type"] == "order" else None,
            "quote_no": info["doc_no"] if info["doc_type"] == "quote" else None,
            "customer_name": info["customer_name"],
            "project_name": info["project_name"],
            "department": info["department"],
            "total_amount": sum(float(i.subtotal or 0) for i in (form.items or [])),
            "status": form.status,
            "accepted_at": form.accepted_at.isoformat() if form.accepted_at else None,
            "accepted_by": form.accepted_by,
            "created_at": form.created_at.isoformat() if form.created_at else None,
        }

    def _to_detail_dict(self, form: AcceptanceForm) -> dict:
        info = self._doc_info(form)
        return {
            "id": str(form.id),
            "acceptance_no": form.acceptance_no,
            "document_id": str(form.document_id) if form.document_id else None,
            # Backward-compat aliases
            "order_id": str(form.document_id) if (info["doc_type"] == "order") else None,
            "quote_id": str(form.document_id) if (info["doc_type"] == "quote") else None,
            "order_no": info["doc_no"] if info["doc_type"] == "order" else None,
            "quote_no": info["doc_no"] if info["doc_type"] == "quote" else None,
            "customer_name": info["customer_name"],
            "customer_phone": info["customer_phone"],
            "customer_address": info["customer_address"],
            "contact_person": info["contact_person"],
            "contact_phone": info["contact_phone"],
            "order_date": info["order_date"],
            "project_name": info["project_name"],
            "department": info["department"],
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
                    "document_item_id": str(item.document_item_id) if item.document_item_id else None,
                    "order_item_id": str(item.document_item_id) if item.document_item_id else None,  # backward compat
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
