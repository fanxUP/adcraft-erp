from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.workflows import ORDER_WORKFLOW, QUOTE_WORKFLOW, allowed_targets
from app.repositories.business_document_repo import BusinessDocumentRepository
from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.models.task import DesignTask, ProductionTask, InstallationTask
from app.models.outsource import OutsourceTask
from app.models.project_cost import ProjectCost
from app.services.quote_calculation import (
    calculate_quote_item_values,
    calculate_quote_totals,
    normalize_quote_item_data,
)
from app.services.order_customer_service import ensure_document_customer


def _build_spec(item) -> str | None:
    """Build specification string from item dimensions + pieces."""
    parts = []
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

ORDER_TRANSITIONS = ORDER_WORKFLOW
QUOTE_TRANSITIONS = QUOTE_WORKFLOW


class BusinessDocumentService:
    """统一业务单据服务 — 按 doc_type 处理订单/报价的 CRUD、转换、状态流转。"""

    def __init__(
        self,
        db: AsyncSession,
        doc_type: str | None = None,
        quote_mode: str | None = None,
    ):
        self.db = db
        self.doc_type = doc_type  # 'order', 'quote', or None
        self.quote_mode = quote_mode or ("regular" if doc_type == "quote" else None)
        self.repo = BusinessDocumentRepository(db, doc_type, self.quote_mode)

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

        data = dict(data)
        if self.doc_type == 'quote':
            data.setdefault("status", "draft")
            data["doc_type"] = "quote"
            data["quote_mode"] = self.quote_mode or "regular"
            if not data.get("doc_no"):
                data["doc_no"] = await generate_quote_no(self.db)
            data.setdefault("subtotal_amount", Decimal("0"))
            data.setdefault("discount_amount", Decimal(str(data.pop("discount_amount", "0"))))
            data.setdefault("tax_rate", Decimal(str(data.pop("tax_rate", "0"))))
            data.setdefault("tax_amount", Decimal("0"))
            data.setdefault("total_amount", Decimal("0"))
            data["items"] = [
                normalize_quote_item_data(item)
                for item in data.get("items", [])
            ]
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
        if doc.doc_type == "quote":
            await self._calculate_quote(doc.id)
        # Refresh to load relationships (e.g. customer) in async context
        await self.db.refresh(doc, ["customer", "items", "status_logs"])
        # 自动同步客户协议价
        await self._sync_customer_agreements(doc)
        # 反向同步联系人：单据里填的联系人自动存入客户管理的联系人列表
        await self._sync_contact_to_customer(doc, data)
        return self._to_detail(doc)

    # ═══════════════════════════════════════════
    # 更新
    # ═══════════════════════════════════════════

    async def update(self, doc_id: UUID, data: dict) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        if doc.doc_type == "quote" and doc.status != "draft":
            raise ValueError("仅草稿报价可以编辑，请先撤回为草稿")

        data = dict(data)
        if doc.doc_type == "quote" and data.get("items") is not None:
            data["items"] = [
                normalize_quote_item_data(item)
                for item in data["items"]
            ]
        if doc.doc_type == "quote" and (
            "customer_id" in data or "customer_name" in data
        ):
            customer_id = data.pop("customer_id", None)
            customer_name = (data.pop("customer_name", None) or "").strip()
            if customer_id:
                doc.customer_id = (
                    customer_id
                    if isinstance(customer_id, UUID)
                    else UUID(str(customer_id))
                )
                doc.customer_name = None
            elif customer_name:
                doc.customer_id = None
                doc.customer_name = customer_name
            else:
                raise ValueError("请选择已有客户或输入新客户名称")

        updated = await self.repo.update(doc, data)

        # 报价更新后重新计算金额
        if updated.doc_type == "quote":
            await self._calculate_quote(doc_id)
            # 重新加载明细，确保协议价同步读取的是本次更新后的最新价格
            # （repo.update 只是替换了行，不会刷新内存中的 doc.items 集合）
            updated.items = await self.repo.get_items(doc_id)
            # 自动同步客户协议价
            await self._sync_customer_agreements(updated)

        # 反向同步联系人：单据里填的联系人自动存入客户管理的联系人列表
        await self._sync_contact_to_customer(updated, data)

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
        # 直接查询（不过滤 deleted_at），因为取消操作已标记软删除
        from app.models.business_document import BusinessDocument
        q = select(BusinessDocument).where(BusinessDocument.id == doc_id)
        result = await self.db.execute(q)
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        if doc.doc_type == "quote":
            return await self._hard_delete_quote(doc)
        else:
            return await self._soft_delete_order(doc)

    async def delete_preview(self, doc_id: UUID) -> dict:
        """返回硬删除前的有效关联数量，不包含已软删除记录。"""
        from app.models.acceptance import AcceptanceForm
        from app.models.business_document import BusinessDocumentItem
        from app.models.contract import ContractDocument
        from app.models.outsource import OutsourceTask
        from app.models.project_cost import ProjectCost
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("报价单不存在")
        if doc.doc_type != "quote":
            raise ValueError("仅支持预览报价单硬删除")
        checks = {
            "报价明细": select(BusinessDocumentItem).where(BusinessDocumentItem.document_id == doc_id),
            "验收单": select(AcceptanceForm).where(AcceptanceForm.document_id == doc_id, AcceptanceForm.deleted_at.is_(None)),
            "合同关联": select(ContractDocument).where(ContractDocument.document_id == doc_id),
            "外协任务": select(OutsourceTask).where(OutsourceTask.related_doc_id == doc_id, OutsourceTask.deleted_at.is_(None)),
            "项目成本": select(ProjectCost).where(ProjectCost.document_id == doc_id),
        }
        associations = []
        for label, query in checks.items():
            count = len((await self.db.execute(query)).scalars().all())
            if count:
                associations.append({"label": label, "count": count})
        return {"quote_no": doc.doc_no, "associations": associations}

    async def _soft_delete_order(self, doc) -> bool:
        if doc.status != "cancelled":
            raise ValueError("只有已取消的订单可以删除")
        await self.repo.soft_delete(doc)
        return True

    async def _hard_delete_quote(self, doc) -> bool:
        """硬删除报价 — 清理所有关联 FK 引用（集成自 quote_service.delete_quote）。"""
        from app.models.contract import ContractDocument
        from app.models.framework_contract import FrameworkContractProjectDocument
        from app.models.acceptance import AcceptanceForm
        from app.models.outsource import OutsourcePayment
        from app.models.cdr_quote import QuoteVersion

        # 1. 删除外协任务及付款
        tasks = (await self.db.execute(
            select(OutsourceTask).where(
                (OutsourceTask.related_doc_id == doc.id)
                & (OutsourceTask.related_doc_type == "quote")
            )
        )).scalars().all()
        if tasks:
            # Batch-fetch all payments for all tasks in one query
            task_ids = [t.id for t in tasks]
            payments = (await self.db.execute(
                select(OutsourcePayment).where(OutsourcePayment.task_id.in_(task_ids))
            )).scalars().all()
            for p in payments:
                await self.db.delete(p)
            for t in tasks:
                await self.db.delete(t)

        # 2. 清理合同关联
        links = (await self.db.execute(
            select(ContractDocument).where(ContractDocument.document_id == doc.id)
        )).scalars().all()
        for l in links:
            await self.db.delete(l)

        # 3. 清理框架合同关联
        fw_links = (await self.db.execute(
            select(FrameworkContractProjectDocument).where(
                FrameworkContractProjectDocument.document_id == doc.id
            )
        )).scalars().all()
        for l in fw_links:
            await self.db.delete(l)

        # 4. 软删除验收单
        acceptances = (await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc.id,
            )
        )).scalars().all()
        for a in acceptances:
            a.deleted_at = datetime.now()
            # 验收单保留在回收记录中，但解除对报价主记录的外键引用。
            a.document_id = None

        # 5. 清除项目成本引用
        costs = (await self.db.execute(
            select(ProjectCost).where(ProjectCost.document_id == doc.id)
        )).scalars().all()
        for c in costs:
            c.document_id = None
            c.document_item_id = None

        # 6. 删除所有关联的报价相关记录（防止 FK 约束阻止主记录删除）
        from sqlalchemy import text as sa_text
        qid_param = str(doc.id)
        # 验收历史保留，但解除其对报价明细的外键引用。
        await self.db.execute(
            sa_text("""
                UPDATE acceptance_items
                SET document_item_id = NULL
                WHERE document_item_id IN (
                    SELECT id FROM business_document_items WHERE document_id = :qid
                )
            """),
            {"qid": qid_param},
        )
        for tbl in [
            "quote_approvals",
            "quote_audit_logs",
            "quote_geometry",
            "business_document_status_logs",
            "business_document_versions",
            "business_document_items",
        ]:
            column = "document_id" if tbl.startswith("business_document_") else "quote_id"
            await self.db.execute(
                sa_text(f"DELETE FROM {tbl} WHERE {column} = :qid"),
                {"qid": qid_param}
            )

        # 删除报价版本及关联明细
        await self.db.execute(
            sa_text("DELETE FROM quote_line_processes WHERE line_id IN (SELECT id FROM quote_lines WHERE version_id IN (SELECT id FROM quote_versions WHERE quote_id = :qid))"),
            {"qid": qid_param}
        )
        await self.db.execute(
            sa_text("DELETE FROM quote_lines WHERE version_id IN (SELECT id FROM quote_versions WHERE quote_id = :qid)"),
            {"qid": qid_param}
        )
        await self.db.execute(
            sa_text("DELETE FROM quote_versions WHERE quote_id = :qid"),
            {"qid": qid_param}
        )

        # 删除图纸快照
        await self.db.execute(
            sa_text("DELETE FROM drawing_snapshots WHERE quote_id = :qid"),
            {"qid": qid_param}
        )

        # 7. 硬删除主记录
        await self.db.delete(doc)
        await self.db.flush()
        return True

    # ═══════════════════════════════════════════
    # 状态流转
    # ═══════════════════════════════════════════

    async def change_status(
        self,
        doc_id: UUID,
        to_status: str,
        reason: str | None,
        operated_by: UUID,
        *,
        acceptance_id: UUID | None = None,
    ) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")

        from_status = doc.status
        transitions = ORDER_TRANSITIONS if doc.doc_type == "order" else QUOTE_TRANSITIONS
        allowed = allowed_targets(transitions, from_status)
        if to_status not in allowed:
            raise ValueError(f"不允许从 {from_status} 流转到 {to_status}")

        # ── 状态闸门：前置条件检查 ──
        if doc.doc_type == "order":
            if to_status == "cancelled" and float(doc.paid_amount or 0) > 0:
                raise ValueError("订单已有收款，请先作废相关收款记录后再取消")
            if from_status == "confirmed" and to_status == "designing":
                await self._auto_create_design_task(doc)
            elif from_status == "designing" and to_status == "in_production":
                await self._require_all_tasks_completed(
                    doc_id,
                    DesignTask,
                    "design_no",
                    "设计",
                    terminal_statuses=("completed",),
                )
            elif from_status == "in_production" and to_status == "in_installation":
                await self._require_all_tasks_completed(
                    doc_id, ProductionTask, "production_no", "生产"
                )
            elif from_status == "in_installation" and to_status == "pending_acceptance":
                await self._require_all_tasks_completed(
                    doc_id, InstallationTask, "installation_no", "安装"
                )
            elif from_status == "pending_acceptance" and to_status == "completed":
                await self._require_acceptance_completion_source(
                    doc_id,
                    acceptance_id,
                )
        elif to_status == "confirmed":
            if not doc.items:
                raise ValueError("请先添加报价明细再确认报价")
            await self._calculate_quote(doc_id)



        await self.repo.update(doc, {"status": to_status})
        await self.repo.create_status_log(doc_id, from_status, to_status, reason, operated_by)

        # ── 确认订单后自动推进到设计中 ──
        if doc.doc_type == "order" and to_status == "confirmed":
            await self._auto_create_design_task(doc)
            doc.status = "designing"
            await self.repo.create_status_log(doc_id, "confirmed", "designing", "订单已确认，系统自动推进", operated_by)
            await self.db.flush()

        # 安装完成 → 自动创建验收单，验收通过后才完成订单
        if doc.doc_type == "order" and to_status == "pending_acceptance":
            await self._auto_create_acceptance(doc)

        # 订单完成 → 生成收款提醒
        if doc.doc_type == "order" and to_status == "completed":
            if doc.unpaid_amount and float(doc.unpaid_amount) > 0 and doc.sales_user_id:
                from app.models.notification import Notification
                reminder = Notification(
                    user_id=doc.sales_user_id,
                    type="payment_reminder",
                    title=f"收款提醒: {doc.doc_no}",
                    content=f"订单 {doc.project_name} 已完成，尚有 {float(doc.unpaid_amount):.2f} 元未收款，请及时跟进。",
                    link=f"/orders/{doc.id}",
                )
                self.db.add(reminder)
                await self.db.flush()


        # 订单取消 → 进回收站
        if doc.doc_type == "order" and to_status == "cancelled":
            await self._cancel_open_tasks(doc_id)
            doc.deleted_at = datetime.now()
            await self.db.flush()

        # 通知
        if doc.sales_user_id and doc.sales_user_id != operated_by:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            labels = {
                "pending_confirm": "待确认", "confirmed": "已确认", "designing": "设计中",
                "in_production": "生产中", "in_installation": "安装中",
                "pending_acceptance": "待验收", "completed": "已完成",
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

    async def _cancel_open_tasks(self, doc_id: UUID) -> None:
        """订单取消后关闭未完任务和验收，避免交付链继续推进。"""
        task_rules = (
            (DesignTask, {"confirmed"}),
            (ProductionTask, {"completed"}),
            (InstallationTask, {"completed"}),
        )
        for model, terminal_statuses in task_rules:
            result = await self.db.execute(
                select(model).where(model.document_id == doc_id)
            )
            for task in result.scalars().all():
                if task.status not in terminal_statuses:
                    task.status = "cancelled"

        from app.models.acceptance import AcceptanceForm

        acceptance_result = await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc_id,
                AcceptanceForm.deleted_at.is_(None),
                AcceptanceForm.status != "accepted",
            )
        )
        for form in acceptance_result.scalars().all():
            form.deleted_at = datetime.now()
        await self.db.flush()

    async def reopen_completed_order(self, doc_id: UUID, reason: str, operated_by: UUID) -> dict:
        """管理员专用：将已完成订单退回待验收，供后续取消或纠正。"""
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("订单不存在")
        if doc.doc_type != "order" or doc.status != "completed":
            raise ValueError("只有已完成订单可以撤回")
        if not reason.strip():
            raise ValueError("撤回原因不能为空")
        await self.repo.update(doc, {"status": "pending_acceptance"})
        await self.repo.create_status_log(doc_id, "completed", "pending_acceptance", reason.strip(), operated_by)
        return self._to_detail(doc)

    async def _require_acceptance_completion_source(
        self,
        doc_id: UUID,
        acceptance_id: UUID | None,
    ) -> None:
        """仅允许验收服务凭待确认验收单完成订单。"""
        if not acceptance_id:
            raise ValueError("请通过验收单确认验收后完成订单")

        from app.models.acceptance import AcceptanceForm

        result = await self.db.execute(
            select(AcceptanceForm.id).where(
                AcceptanceForm.id == acceptance_id,
                AcceptanceForm.document_id == doc_id,
                AcceptanceForm.status == "pending",
                AcceptanceForm.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("验收单与订单不匹配或当前不可确认")

    async def _require_all_tasks_completed(
        self,
        doc_id: UUID,
        model,
        no_attr: str,
        label: str,
        *,
        terminal_statuses: tuple[str, ...] = ("completed",),
    ) -> None:
        # Check all tasks of a given type for this document are completed.
        # Raises ValueError if any task is not completed or none exist.
        r = await self.db.execute(
            select(model).where(model.document_id == doc_id)
        )
        tasks = r.scalars().all()
        if not tasks:
            raise ValueError(f"请先创建{label}任务，再继续流转")
        for t in tasks:
            if t.status not in terminal_statuses:
                task_no = getattr(t, no_attr, "N/A")
                raise ValueError(f"{label}任务 {task_no} 未完成，请先完成后再流转")

    async def _auto_create_acceptance(self, doc) -> None:
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.services.number_generator import generate_acceptance_no

        existing = (await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )).scalars().first()
        if existing:
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
                area=float(item.area) if item.use_area and item.area else None,
                unit_price=float(item.unit_price) if item.unit_price else None,
                subtotal=float(item.subtotal_amount) if item.subtotal_amount else None,
                item_status="pending",
                group_name=item.group_name,
                remark=item.remark,
                image_url=item.image_url,
            )
            self.db.add(acceptance_item)

        await self.db.flush()

    async def _auto_create_design_task(self, doc) -> None:
        from app.models.task import DesignTask
        from app.services.number_generator import generate_design_no

        existing = await self.db.execute(
            select(DesignTask).where(DesignTask.document_id == doc.id)
        )
        if existing.scalar_one_or_none():
            return

        task = DesignTask(
            design_no=await generate_design_no(self.db),
            document_id=doc.id,
            customer_id=doc.customer_id,
            project_name=doc.project_name,
            status="pending",
        )
        self.db.add(task)
        await self.db.flush()

    async def _auto_create_production_task(self, doc) -> None:
        from app.models.task import ProductionTask
        from app.services.number_generator import generate_production_no

        existing = await self.db.execute(
            select(ProductionTask).where(ProductionTask.document_id == doc.id)
        )
        if existing.scalar_one_or_none():
            return

        task = ProductionTask(
            production_no=await generate_production_no(self.db),
            document_id=doc.id,
            customer_id=doc.customer_id,
            project_name=doc.project_name,
            status="pending",
            quantity=1,
        )
        self.db.add(task)
        await self.db.flush()

    async def _auto_create_installation_task(self, doc) -> None:
        from app.models.task import InstallationTask
        from app.services.number_generator import generate_installation_no

        existing = await self.db.execute(
            select(InstallationTask).where(InstallationTask.document_id == doc.id)
        )
        if existing.scalar_one_or_none():
            return

        task = InstallationTask(
            installation_no=await generate_installation_no(self.db),
            document_id=doc.id,
            customer_id=doc.customer_id,
            project_name=doc.project_name,
            status="pending",
        )
        self.db.add(task)
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

        from app.services.order_cost_service import OrderCostAggregationService

        breakdown = await OrderCostAggregationService(self.db).calculate(doc_id)
        return await self.set_cost(doc_id, float(breakdown.total))

    # ═══════════════════════════════════════════
    # 报价计算
    # ═══════════════════════════════════════════


    async def _sync_contact_to_customer(self, doc, data: dict) -> None:
        """单据保存时反向同步：填了联系人则自动存入客户管理的联系人列表（按客户+姓名 upsert）。"""
        contact_person = data.get("contact_person")
        if not doc.customer_id or not contact_person:
            return
        from app.repositories.customer_repo import CustomerRepository
        await CustomerRepository(self.db).upsert_contact(
            doc.customer_id, contact_person, data.get("contact_phone")
        )

    async def _sync_customer_agreements(self, doc) -> None:
        """对于用户手动重新定价的明细行，自动保存为客户协议价。"""
        from datetime import date
        
        if not doc.customer_id:
            return
        if not doc.items:
            return
        
        cdr_repo = CdrQuoteRepository(self.db)
        
        for item in doc.items:
            if not item.product_id:
                continue
            if not item.unit_price or item.unit_price <= 0:
                continue
            
            # 获取产品默认单价
            product = await cdr_repo.get_product(item.product_id)
            if not product:
                continue
            
            product_price = product.default_price or 0
            
            # 检查已有协议价
            existing = await cdr_repo.get_customer_agreement(doc.customer_id, item.product_id)
            agreement_price = existing.price_value if existing else 0
            
            # 只有产品有默认价时才能可靠判断是否手动定价
            if product_price <= 0:
                continue
            
            # 如果单价与产品默认价和已有协议价都不同 → 用户手动定价
            item_price = item.unit_price
            if item_price == product_price or item_price == agreement_price:
                continue  # 不是手动定价，跳过
            
            # 创建或更新协议价
            agreement_data = {
                "customer_id": doc.customer_id,
                "product_id": item.product_id,
                "pricing_method": product.pricing_method or "quantity",
                "price_value": item_price,
                "minimum_charge": existing.minimum_charge if existing else (product.min_charge or 0),
                "discount_rate": existing.discount_rate if existing else Decimal("1"),
                "effective_from": str(date.today()),
                "effective_to": None,
            }
            
            if existing:
                await cdr_repo.update_customer_agreement(existing.id, agreement_data)
            else:
                await cdr_repo.create_customer_agreement(agreement_data)

    async def _calculate_quote(self, doc_id: UUID) -> None:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "quote":
            return
        items = await self.repo.get_items(doc_id)
        for item in items:
            values = calculate_quote_item_values(
                {
                    "width": item.width,
                    "width_unit": item.width_unit,
                    "height": item.height,
                    "height_unit": item.height_unit,
                    "pieces": item.pieces,
                    "quantity": item.quantity,
                    "use_area": item.use_area,
                    "unit_price": item.unit_price,
                    "process_fee": item.process_fee,
                    "installation_fee": item.installation_fee,
                    "design_fee": item.design_fee,
                    "transport_fee": item.transport_fee,
                    "other_fee": item.other_fee,
                }
            )
            item.area = values["area"]
            item.subtotal_amount = values["subtotal_amount"]
        totals = calculate_quote_totals(
            [item.subtotal_amount for item in items],
            discount_amount=doc.discount_amount,
            tax_rate=doc.tax_rate,
        )

        await self.repo.update(doc, totals)

    # ═══════════════════════════════════════════
    # 核心：类型转换（订单 ↔ 报价）
    # ═══════════════════════════════════════════

    async def convert_doc_type(self, doc_id: UUID, new_type: str,
                                created_by: UUID) -> dict:
        """统一转换方法 — 只改 doc_type + 编号，ID 不变，所有 FK 自动跟随。"""
        # 直接查询（不过滤 deleted_at），因为已取消的订单已被软删除
        from app.models.business_document import BusinessDocument
        q = select(BusinessDocument).where(BusinessDocument.id == doc_id)
        result = await self.db.execute(q)
        doc = result.scalar_one_or_none()
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
            await ensure_document_customer(self.db, doc, created_by)
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
            doc.paid_amount = 0
            doc.unpaid_amount = doc.total_amount
            doc.cost_amount = 0
            doc.gross_profit = doc.total_amount
            # 标记来源报价ID
            doc.source_quote_id = doc.id

            # 清理该文档下残留的孤立任务和验收单，避免阻塞后续自动推进
            from app.models.acceptance import AcceptanceForm
            for model_cls in (DesignTask, ProductionTask, InstallationTask):
                result = await self.db.execute(
                    select(model_cls).where(
                        model_cls.document_id == doc_id,
                        model_cls.status == "pending"
                    )
                )
                for t in result.scalars().all():
                    t.status = "cancelled"
            ac_result = await self.db.execute(
                select(AcceptanceForm).where(
                    AcceptanceForm.document_id == doc_id,
                    AcceptanceForm.status == "draft",
                    AcceptanceForm.deleted_at.is_(None),
                )
            )
            for form in ac_result.scalars().all():
                form.deleted_at = datetime.now()
        else:  # new_type == "quote"
            doc.doc_no = await generate_quote_no(self.db)
            doc.doc_type = "quote"
            doc.status = "draft"
            # 重置订单专有字段
            doc.paid_amount = 0
            doc.unpaid_amount = 0
            # 取消软删除（已取消订单被标记了 deleted_at）
            doc.deleted_at = None

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
        # 订单取消会连带取消下游任务、软删验收单，恢复时一并还原，避免交付链卡死
        if doc.doc_type == "order":
            await self._restore_delivery_chain(doc_id)
        doc.status = await self._pre_cancel_status(doc)
        await self.db.flush()
        return self._to_detail(doc)

    async def _pre_cancel_status(self, doc) -> str:
        """取消前状态：取最近一次进入 cancelled 的状态日志的 from_status，取不到则回退到初始可流转状态。"""
        from app.models.business_document import BusinessDocumentStatusLog

        result = await self.db.execute(
            select(BusinessDocumentStatusLog)
            .where(
                BusinessDocumentStatusLog.document_id == doc.id,
                BusinessDocumentStatusLog.to_status == "cancelled",
            )
            .order_by(BusinessDocumentStatusLog.operated_at.desc())
            .limit(1)
        )
        log = result.scalar_one_or_none()
        if log and log.from_status:
            return log.from_status
        return "pending_confirm" if doc.doc_type == "order" else "draft"

    async def _restore_delivery_chain(self, doc_id: UUID) -> None:
        """还原取消对交付链的影响：被取消的任务重置为可推进状态，被软删的验收单恢复。"""
        for model in (DesignTask, ProductionTask, InstallationTask):
            result = await self.db.execute(
                select(model).where(
                    model.document_id == doc_id,
                    model.status == "cancelled",
                )
            )
            for task in result.scalars().all():
                task.status = "pending"

        from app.models.acceptance import AcceptanceForm

        result = await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc_id,
                AcceptanceForm.deleted_at.isnot(None),
            )
        )
        for form in result.scalars().all():
            form.deleted_at = None
        await self.db.flush()

    # ═══════════════════════════════════════════
    # 明细
    # ═══════════════════════════════════════════

    async def add_items(self, doc_id: UUID, items_data: list[dict]) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        if doc.doc_type == "quote" and doc.status != "draft":
            raise ValueError("仅草稿报价可以编辑，请先撤回为草稿")
        normalized_items = [
            normalize_quote_item_data(item)
            for item in items_data
        ]
        await self.repo.add_items(doc_id, normalized_items)
        if doc.doc_type == "quote":
            await self._calculate_quote(doc_id)
        return self._to_detail(await self.repo.get_by_id(doc_id))

    async def add_item(self, doc_id: UUID, data: dict) -> dict:
        item_data = dict(data)
        item_data.pop("id", None)
        return await self.add_items(doc_id, [item_data])

    async def update_item(
        self,
        doc_id: UUID,
        item_id: UUID,
        data: dict,
    ) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("报价单不存在")
        if doc.status != "draft":
            raise ValueError("仅草稿报价可以编辑，请先撤回为草稿")
        item = await self.repo.get_item(item_id, document_id=doc_id)
        if not item:
            raise ValueError("报价明细不存在或不属于当前报价")

        update_data = dict(data)
        merged = {
            "width": item.width,
            "width_unit": item.width_unit,
            "height": item.height,
            "height_unit": item.height_unit,
            "pieces": item.pieces,
            "quantity": item.quantity,
            "use_area": item.use_area,
            "unit_price": item.unit_price,
            "process_fee": item.process_fee,
            "installation_fee": item.installation_fee,
            "design_fee": item.design_fee,
            "transport_fee": item.transport_fee,
            "other_fee": item.other_fee,
            **update_data,
        }
        update_data.update(calculate_quote_item_values(merged))
        await self.repo.update_item(item, update_data)
        await self._calculate_quote(doc_id)
        return self._to_detail(await self.repo.get_by_id(doc_id))

    async def delete_item(self, doc_id: UUID, item_id: UUID) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("报价单不存在")
        if doc.status != "draft":
            raise ValueError("仅草稿报价可以编辑，请先撤回为草稿")
        item = await self.repo.get_item(item_id, document_id=doc_id)
        if not item:
            raise ValueError("报价明细不存在或不属于当前报价")
        await self.repo.delete_item(item)
        await self._calculate_quote(doc_id)
        return self._to_detail(await self.repo.get_by_id(doc_id))

    # ═══════════════════════════════════════════
    # 序列化
    # ═══════════════════════════════════════════

    @staticmethod
    def _to_ref(d) -> dict:
        """标准单据引用 — 项目中所有嵌套/列表场景统一使用此方法。
        返回字段：id, doc_type, doc_no, project_name, customer_name,
        department, status, total_amount (+ order 专有 paid/unpaid)。
        调用方如需额外字段，在返回 dict 上叠加即可。
        """
        base = {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "doc_no": d.doc_no,
            "project_name": d.project_name or "",
            "customer_name": d.customer_name or (d.customer.name if d.customer else None),
            "department": d.department or "",
            "status": d.status or "",
            "total_amount": float(d.total_amount) if d.total_amount else 0,
        }
        if d.doc_type == "quote":
            base["quote_mode"] = d.quote_mode
        if d.doc_type == "order":
            base["order_no"] = d.doc_no
            base["paid_amount"] = float(d.paid_amount) if d.paid_amount else 0
            base["unpaid_amount"] = float(d.unpaid_amount) if d.unpaid_amount else 0
        else:
            base["quote_no"] = d.doc_no
        return base

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
                "order_no": d.doc_no,
                "paid_amount": float(d.paid_amount),
                "unpaid_amount": float(d.unpaid_amount),
                "cost_amount": float(d.cost_amount),
                "gross_profit": float(d.gross_profit),
            })
        else:
            base.update({
                "quote_no": d.doc_no,
                "quote_mode": d.quote_mode,
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
                    "image_url": it.image_url,
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
                "quote_mode": d.quote_mode,
                "subtotal_amount": float(d.subtotal_amount),
                "discount_amount": float(d.discount_amount),
                "tax_rate": float(d.tax_rate),
                "tax_amount": float(d.tax_amount),
                "valid_until": d.valid_until.isoformat() if d.valid_until else None,
            })

        return base
