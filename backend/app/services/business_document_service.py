from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.repositories.business_document_repo import BusinessDocumentRepository
from app.models.outsource import OutsourceTask
from app.models.inventory import StockRecord
from app.models.project_cost import ProjectCost


def _build_spec(item) -> str | None:
    """Build specification string from item dimensions + pieces."""
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


# ── 状态机 ──

ORDER_TRANSITIONS = {
    "pending_confirm": ["confirmed", "cancelled"],
    "confirmed": ["designing", "cancelled"],
    "designing": ["in_production", "in_installation", "completed", "cancelled"],
    "in_production": ["designing", "in_installation", "completed", "cancelled"],
    "in_installation": ["designing", "in_production", "completed", "cancelled"],
    "completed": ["designing", "in_production", "in_installation", "cancelled"],
    "cancelled": [],
}

QUOTE_TRANSITIONS = {
    "draft": ["confirmed", "cancelled"],
    "confirmed": ["converted", "cancelled", "draft"],
    "cancelled": [],
    "converted": [],  # 终端状态
}


class BusinessDocumentService:
    """统一业务单据服务 — 按 doc_type 处理订单/报价的 CRUD、转换、状态流转。"""

    def __init__(self, db: AsyncSession, doc_type: str | None = None):
        self.db = db
        self.doc_type = doc_type  # 'order', 'quote', or None
        self.repo = BusinessDocumentRepository(db, doc_type)

    # ═══════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════

    async def list_all(self, page: int, page_size: int, status: str | None = None,
                       customer_id: UUID | None = None, keyword: str | None = None,
                       exclude_status: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        docs, total = await self.repo.list_all(
            skip=skip, limit=page_size, status=status,
            customer_id=customer_id, keyword=keyword, exclude_status=exclude_status,
        )
        return [self._to_summary(d) for d in docs], total

    async def get_by_id(self, doc_id: UUID) -> dict | None:
        doc = await self.repo.get_by_id(doc_id)
        return self._to_detail(doc) if doc else None

    async def list_deleted(self, page: int, page_size: int,
                           keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        docs, total = await self.repo.list_deleted(skip=skip, limit=page_size, keyword=keyword)
        return [self._to_summary(d) for d in docs], total

    # ═══════════════════════════════════════════
    # 创建
    # ═══════════════════════════════════════════

    async def create(self, data: dict) -> dict:
        from app.services.number_generator import generate_quote_no

        if self.doc_type == 'quote':
            data.setdefault("status", "draft")
            data["doc_type"] = "quote"
            if not data.get("doc_no"):
                data["doc_no"] = await generate_quote_no(self.db)
            data.setdefault("subtotal_amount", Decimal("0"))
            data.setdefault("discount_amount", Decimal(str(data.pop("discount_amount", "0"))))
            data.setdefault("tax_rate", Decimal(str(data.pop("tax_rate", "0"))))
            data.setdefault("tax_amount", Decimal("0"))
            data.setdefault("total_amount", Decimal("0"))
        else:
            # Default to order creation
            data.setdefault("status", "pending_confirm")
            data["doc_type"] = "order"
            data.setdefault("total_amount", Decimal("0"))

        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        if data.get("sales_user_id"):
            data["sales_user_id"] = UUID(data["sales_user_id"])

        doc = await self.repo.create(data)
        return self._to_detail(doc)

    # ═══════════════════════════════════════════
    # 更新
    # ═══════════════════════════════════════════

    async def update(self, doc_id: UUID, data: dict) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")

        updated = await self.repo.update(doc, data)

        # 报价更新后重新计算金额
        if updated.doc_type == "quote":
            await self._calculate_quote(doc_id)

        # 同步外协任务
        if data.get("project_name") or data.get("total_amount"):
            from app.models.outsource import OutsourceTask
            tasks = (await self.db.execute(
                select(OutsourceTask).where(
                    (OutsourceTask.related_doc_id == doc_id)
                    & (OutsourceTask.related_doc_type == updated.doc_type)
                )
            )).scalars().all()
            for t in tasks:
                if data.get("project_name"):
                    t.description = data["project_name"]
                if data.get("total_amount") is not None:
                    t.unit_price = float(data["total_amount"])
                    t.total_amount = float(data["total_amount"])
            if tasks:
                await self.db.flush()

        return self._to_detail(updated)

    # ═══════════════════════════════════════════
    # 删除
    # ═══════════════════════════════════════════

    async def delete(self, doc_id: UUID) -> bool:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            return False

        if doc.doc_type == "quote":
            return await self._hard_delete_quote(doc)
        else:
            return await self._soft_delete_order(doc)

    async def _soft_delete_order(self, doc) -> bool:
        if doc.status != "cancelled":
            raise ValueError("只有已取消的订单可以删除")
        await self.repo.soft_delete(doc)
        return True

    async def _hard_delete_quote(self, doc) -> bool:
        """硬删除报价 — 清理所有关联 FK 引用（集成自 quote_service.delete_quote）。"""
        from app.models.contract import ContractQuote
        from app.models.framework_contract import FrameworkContractProjectQuote
        from app.models.acceptance import AcceptanceForm

        # 1. 删除外协任务及付款
        tasks = (await self.db.execute(
            select(OutsourceTask).where(
                (OutsourceTask.related_doc_id == doc.id)
                & (OutsourceTask.related_doc_type == "quote")
            )
        )).scalars().all()
        for t in tasks:
            from app.models.outsource import OutsourcePayment
            payments = (await self.db.execute(
                select(OutsourcePayment).where(OutsourcePayment.task_id == t.id)
            )).scalars().all()
            for p in payments:
                await self.db.delete(p)
            await self.db.delete(t)

        # 2. 清理合同关联
        links = (await self.db.execute(
            select(ContractQuote).where(ContractQuote.quote_id == doc.id)
        )).scalars().all()
        for l in links:
            await self.db.delete(l)

        # 3. 清理框架合同关联
        fw_links = (await self.db.execute(
            select(FrameworkContractProjectQuote).where(
                FrameworkContractProjectQuote.quote_id == doc.id
            )
        )).scalars().all()
        for l in fw_links:
            await self.db.delete(l)

        # 4. 软删除验收单
        acceptances = (await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )).scalars().all()
        for a in acceptances:
            a.deleted_at = datetime.now()

        # 5. 清除项目成本引用
        costs = (await self.db.execute(
            select(ProjectCost).where(ProjectCost.document_id == doc.id)
        )).scalars().all()
        for c in costs:
            c.document_id = None
            c.document_item_id = None

        # 6. 硬删除主记录
        await self.db.delete(doc)
        await self.db.flush()
        return True

    # ═══════════════════════════════════════════
    # 状态流转
    # ═══════════════════════════════════════════

    async def change_status(self, doc_id: UUID, to_status: str,
                            reason: str | None, operated_by: UUID) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")

        from_status = doc.status
        transitions = ORDER_TRANSITIONS if doc.doc_type == "order" else QUOTE_TRANSITIONS
        allowed = transitions.get(from_status, [])
        if to_status not in allowed:
            raise ValueError(f"不允许从 {from_status} 流转到 {to_status}")

        await self.repo.update(doc, {"status": to_status})
        await self.repo.create_status_log(doc_id, from_status, to_status, reason, operated_by)

        # 订单完成 → 自动创建验收单
        if doc.doc_type == "order" and to_status == "completed":
            await self._auto_create_acceptance(doc)

        # 订单取消 → 进回收站
        if doc.doc_type == "order" and to_status == "cancelled":
            doc.deleted_at = datetime.now()
            await self.db.flush()

        # 通知
        if doc.sales_user_id and doc.sales_user_id != operated_by:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            labels = {
                "pending_confirm": "待确认", "confirmed": "已确认", "designing": "设计中",
                "in_production": "生产中", "in_installation": "安装中", "completed": "已完成",
                "cancelled": "已取消", "draft": "草稿", "converted": "已转换",
            }
            await notif_svc.create_system_notification(
                user_id=doc.sales_user_id,
                type_="order_status",
                title=f"单据状态变更: {doc.doc_no}",
                content=f"{doc.project_name} 状态从 {labels.get(from_status, from_status)} 变更为 {labels.get(to_status, to_status)}",
                link=f"/{'orders' if doc.doc_type == 'order' else 'quotes'}/{doc_id}",
            )

        return self._to_detail(doc)

    async def _auto_create_acceptance(self, doc) -> None:
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.services.number_generator import generate_acceptance_no

        existing = await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            return

        acceptance_no = await generate_acceptance_no(self.db)
        form = AcceptanceForm(
            acceptance_no=acceptance_no,
            document_id=doc.id,
            status="draft",
        )
        self.db.add(form)
        await self.db.flush()

        for item in doc.items or []:
            spec = _build_spec(item)
            acceptance_item = AcceptanceItem(
                acceptance_id=form.id,
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
            self.db.add(acceptance_item)

        await self.db.flush()

    # ═══════════════════════════════════════════
    # 订单成本
    # ═══════════════════════════════════════════

    async def set_cost(self, doc_id: UUID, cost_amount: float) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        if doc.doc_type != "order":
            raise ValueError("仅订单可设置成本")
        cost = Decimal(str(cost_amount))
        total = Decimal(str(doc.total_amount))
        gross_profit = total - cost
        await self.repo.update(doc, {
            "cost_amount": float(cost),
            "gross_profit": float(gross_profit),
        })
        return self._to_detail(doc)

    async def auto_calculate_cost(self, doc_id: UUID) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        if doc.doc_type != "order":
            raise ValueError("仅订单可自动计算成本")

        total_cost = Decimal("0")

        r = await self.db.execute(
            select(func.coalesce(func.sum(OutsourceTask.total_amount), 0))
            .where(OutsourceTask.related_doc_id == doc_id, OutsourceTask.status.in_(["completed", "settled"]))
        )
        total_cost += Decimal(str(r.scalar()))

        r = await self.db.execute(
            select(func.coalesce(func.sum(StockRecord.total_cost), 0))
            .where(StockRecord.document_id == doc_id, StockRecord.record_type == "out")
        )
        total_cost += Decimal(str(r.scalar()))

        r = await self.db.execute(
            select(func.coalesce(func.sum(ProjectCost.amount), 0))
            .where(ProjectCost.document_id == doc_id, ProjectCost.deleted_at.is_(None))
        )
        total_cost += Decimal(str(r.scalar()))

        return await self.set_cost(doc_id, float(total_cost))

    # ═══════════════════════════════════════════
    # 报价计算
    # ═══════════════════════════════════════════

    async def _calculate_quote(self, doc_id: UUID) -> None:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "quote":
            return
        items = await self.repo.get_items(doc_id)
        subtotal = sum(
            Decimal(str(it.subtotal_amount)) if it.subtotal_amount else
            Decimal(str(it.unit_price)) * Decimal(str(it.quantity))
            for it in items
        )
        discount = Decimal(str(doc.discount_amount or 0))
        tax_rate = Decimal(str(doc.tax_rate or 0))
        taxable = subtotal - discount
        tax_amount = taxable * tax_rate / Decimal("100")
        total = taxable + tax_amount

        await self.repo.update(doc, {
            "subtotal_amount": float(subtotal),
            "tax_amount": float(tax_amount),
            "total_amount": float(total),
        })

    # ═══════════════════════════════════════════
    # 核心：类型转换（订单 ↔ 报价）
    # ═══════════════════════════════════════════

    async def convert_doc_type(self, doc_id: UUID, new_type: str,
                                created_by: UUID) -> dict:
        """统一转换方法 — 只改 doc_type + 编号，ID 不变，所有 FK 自动跟随。"""
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")

        old_type = doc.doc_type
        if old_type == new_type:
            raise ValueError(f"已经是{new_type}类型")
        if old_type != "quote" and old_type != "order":
            raise ValueError(f"不支持的类型转换: {old_type}")

        # 转换前验证
        if old_type == "quote" and new_type == "order":
            if doc.status not in ("confirmed",):
                raise ValueError("只有已确认的报价单可以转订单")
        elif old_type == "order" and new_type == "quote":
            if doc.status not in ("cancelled",):
                raise ValueError("只有已取消的订单可以转报价")

        from app.services.number_generator import generate_quote_no, generate_order_no

        # 1. 快照
        ver_no = await self.repo.get_next_version_no(doc_id)
        await self.repo.create_version(doc_id, ver_no, self._to_detail(doc), created_by)

        # 2. 切换类型 & 编号
        if new_type == "order":
            doc.doc_no = await generate_order_no(self.db)
            doc.doc_type = "order"
            doc.status = "pending_confirm"
            # 重置报价专有字段
            doc.discount_amount = 0
            doc.tax_rate = 0
            doc.tax_amount = 0
            doc.valid_until = None
        else:  # new_type == "quote"
            doc.doc_no = await generate_quote_no(self.db)
            doc.doc_type = "quote"
            doc.status = "draft"
            # 重置订单专有字段
            doc.paid_amount = 0
            doc.unpaid_amount = 0

        await self.db.flush()

        # 3. 状态日志
        await self.repo.create_status_log(
            doc_id, None, doc.status,
            f"报价转订单" if new_type == "order" else "订单转报价",
            created_by,
        )

        await self.db.flush()
        # 所有 FK 自动跟随 — document_id 未改变
        return self._to_detail(doc)

    # ═══════════════════════════════════════════
    # 恢复
    # ═══════════════════════════════════════════

    async def restore(self, doc_id: UUID) -> dict:
        doc = await self.repo.get_deleted_by_id(doc_id)
        if not doc:
            raise ValueError("回收站中未找到该单据")
        await self.repo.restore(doc)
        return self._to_detail(doc)

    # ═══════════════════════════════════════════
    # 明细
    # ═══════════════════════════════════════════

    async def add_items(self, doc_id: UUID, items_data: list[dict]) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        for item in items_data:
            for fee_key in ("unit_price", "process_fee", "installation_fee",
                            "design_fee", "transport_fee", "other_fee"):
                item[fee_key] = Decimal(str(item.get(fee_key, "0")))
            item["quantity"] = Decimal(str(item.get("quantity", "1")))
        await self.repo.add_items(doc_id, items_data)
        if doc.doc_type == "quote":
            await self._calculate_quote(doc_id)
        return self._to_detail(await self.repo.get_by_id(doc_id))

    # ═══════════════════════════════════════════
    # 序列化
    # ═══════════════════════════════════════════

    def _to_summary(self, d) -> dict:
        base = {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "doc_no": d.doc_no,
            "customer_id": str(d.customer_id) if d.customer_id else None,
            "customer_name": d.customer_name or (d.customer.name if d.customer else None),
            "project_name": d.project_name,
            "status": d.status,
            "total_amount": float(d.total_amount),
            "department": d.department,
            "contact_person": d.contact_person,
            "contact_phone": d.contact_phone,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
        }
        if d.doc_type == "order":
            base.update({
                # Backward-compat aliases
                "order_no": d.doc_no,
                "paid_amount": float(d.paid_amount),
                "unpaid_amount": float(d.unpaid_amount),
                "cost_amount": float(d.cost_amount),
                "gross_profit": float(d.gross_profit),
            })
        else:
            base.update({
                "quote_no": d.doc_no,
                "valid_until": d.valid_until.isoformat() if d.valid_until else None,
            })
        return base

    def _to_detail(self, d) -> dict:
        base = {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "doc_no": d.doc_no,
            "customer_id": str(d.customer_id) if d.customer_id else None,
            "customer_name": d.customer_name or (d.customer.name if d.customer else None),
            "project_name": d.project_name,
            "sales_user_id": str(d.sales_user_id) if d.sales_user_id else None,
            "status": d.status,
            "total_amount": float(d.total_amount),
            "remark": d.remark,
            "department": d.department,
            "contact_person": d.contact_person,
            "contact_phone": d.contact_phone,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "items": [
                {
                    "id": str(it.id),
                    "item_name": it.item_name,
                    "product_id": str(it.product_id) if it.product_id else None,
                    "material_id": str(it.material_id) if it.material_id else None,
                    "process_id": str(it.process_id) if it.process_id else None,
                    "length": float(it.length) if it.length else None,
                    "length_unit": it.length_unit,
                    "width": float(it.width) if it.width else None,
                    "width_unit": it.width_unit,
                    "height": float(it.height) if it.height else None,
                    "height_unit": it.height_unit,
                    "quantity": float(it.quantity),
                    "unit": it.unit,
                    "use_area": it.use_area,
                    "quantity_mode": it.quantity_mode,
                    "pieces": float(it.pieces) if it.pieces else None,
                    "specification": _build_spec(it),
                    "area": float(it.area) if it.area else None,
                    "unit_price": float(it.unit_price),
                    "process_fee": float(it.process_fee),
                    "installation_fee": float(it.installation_fee),
                    "design_fee": float(it.design_fee),
                    "transport_fee": float(it.transport_fee),
                    "other_fee": float(it.other_fee),
                    "subtotal_amount": float(it.subtotal_amount),
                    "remark": it.remark,
                    "sort_order": it.sort_order,
                    "group_name": it.group_name,
                    "material_process": it.material_process,
                }
                for it in (d.items or [])
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
                for log in (d.status_logs or [])
            ],
        }

        if d.doc_type == "order":
            base.update({
                "order_no": d.doc_no,
                "source_quote_id": str(d.source_quote_id) if d.source_quote_id else None,
                "quote_id": str(d.source_quote_id) if d.source_quote_id else None,  # backward compat
                "paid_amount": float(d.paid_amount),
                "unpaid_amount": float(d.unpaid_amount),
                "cost_amount": float(d.cost_amount),
                "gross_profit": float(d.gross_profit),
                "delivery_deadline": d.delivery_deadline.isoformat() if d.delivery_deadline else None,
                "installation_address": d.installation_address,
                "design_tasks": [
                    {"id": str(t.id), "design_no": t.design_no, "status": t.status, "project_name": t.project_name}
                    for t in (d.design_tasks or [])
                ],
                "production_tasks": [
                    {"id": str(t.id), "production_no": t.production_no, "status": t.status, "project_name": t.project_name}
                    for t in (d.production_tasks or [])
                ],
                "installation_tasks": [
                    {"id": str(t.id), "installation_no": t.installation_no, "status": t.status, "project_name": t.project_name}
                    for t in (d.installation_tasks or [])
                ],
            })
        else:
            base.update({
                "quote_no": d.doc_no,
                "subtotal_amount": float(d.subtotal_amount),
                "discount_amount": float(d.discount_amount),
                "tax_rate": float(d.tax_rate),
                "tax_amount": float(d.tax_amount),
                "valid_until": d.valid_until.isoformat() if d.valid_until else None,
            })

        return base
