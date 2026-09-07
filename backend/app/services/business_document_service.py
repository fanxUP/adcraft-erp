from datetime import datetime, date, timedelta
import hashlib
import hmac
import json
import secrets
from zoneinfo import ZoneInfo
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select

from app.core.config import settings
from app.domain.workflows import ORDER_WORKFLOW, QUOTE_WORKFLOW, allowed_targets
from app.repositories.business_document_repo import BusinessDocumentRepository
from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.models.business_document import BusinessDocument
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
    def value(name):
        return item.get(name) if isinstance(item, dict) else getattr(item, name, None)

    parts = []
    if value("width"):
        v = float(value("width"))
        num = str(int(v)) if v == int(v) else str(v)
        parts.append(f"{num}{value('width_unit') or 'm'}")
    if value("height"):
        v = float(value("height"))
        num = str(int(v)) if v == int(v) else str(v)
        parts.append(f"{num}{value('height_unit') or 'm'}")
    pieces = value("pieces")
    if pieces and float(pieces) > 1:
        parts.append(str(int(float(pieces))))
    return " × ".join(parts) if parts else None


# ── 状态机 ──

ORDER_TRANSITIONS = ORDER_WORKFLOW
QUOTE_TRANSITIONS = QUOTE_WORKFLOW


_BUSINESS_TZ = ZoneInfo("Asia/Shanghai")

ORDER_ITEM_MUTABLE_STATUSES = frozenset({
    "pending_confirm",
    "confirmed",
    "designing",
    "in_production",
    "in_installation",
})
ORDER_ITEM_FIELDS = (
    "product_id",
    "material_id",
    "process_id",
    "item_name",
    "length",
    "length_unit",
    "width",
    "width_unit",
    "height",
    "height_unit",
    "quantity",
    "unit",
    "use_area",
    "quantity_mode",
    "pieces",
    "unit_price",
    "process_fee",
    "installation_fee",
    "design_fee",
    "transport_fee",
    "other_fee",
    "remark",
    "image_url",
    "sort_order",
    "group_name",
    "group_id",
    "material_process",
)
ORDER_EDIT_HEADER_FIELDS = (
    "customer_id",
    "customer_name",
    "project_name",
    "department",
    "contact_person",
    "contact_phone",
    "delivery_deadline",
    "installation_address",
    "remark",
)
MONEY_QUANTUM = Decimal("0.01")
MUTATION_PREVIEW_TTL = timedelta(minutes=10)
_PREVIEW_SIGNING_SECRET = (
    settings.SECRET_KEY or secrets.token_hex(32)
).encode("utf-8")


class OrderItemMutationConflict(ValueError):
    """客户端提交的订单版本已经过期。"""


def _business_today() -> date:
    """业务日期：北京时间今天（服务器为 UTC，直接 date.today() 在凌晨会差一天）。"""
    return datetime.now(_BUSINESS_TZ).date()


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
                       exclude_status: str | list[str] | tuple[str, ...] | None = None) -> tuple[list, int]:
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
            if not data.get("quote_date"):
                # QuoteCreate.model_dump() 会把 None 也带进来，setdefault 无法兜底
                data["quote_date"] = _business_today()
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
        await self.db.refresh(doc, ["customer", "items", "groups", "status_logs"])
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
        groups_supplied = doc.doc_type == "quote" and "groups" in data
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
            if groups_supplied:
                updated.groups = await self.repo.get_groups(doc_id)
            # 自动同步客户协议价
            await self._sync_customer_agreements(updated)

        # 反向同步联系人：单据里填的联系人自动存入客户管理的联系人列表
        await self._sync_contact_to_customer(updated, data)

        # 同步外协任务的项目描述；订单销售金额与外协供应商成本是两个独立口径，
        # 不能因为订单保存而覆盖外协任务的 unit_price/total_amount。
        if data.get("project_name"):
            from app.models.outsource import OutsourceTask
            tasks = (await self.db.execute(
                select(OutsourceTask).where(
                    (OutsourceTask.related_doc_id == doc_id)
                    & (OutsourceTask.related_doc_type == updated.doc_type)
                    & (OutsourceTask.deleted_at.is_(None))
                )
            )).scalars().all()
            for t in tasks:
                t.description = data["project_name"]
            if tasks:
                await self.db.flush()

        # 订单保存后同步关联框架合同项目的 项目名称/部门 为订单最新值（金额不自动覆盖）
        if updated.doc_type == "order":
            await self._sync_framework_contract_projects(updated)

        return self._to_detail(updated)

    async def _sync_framework_contract_projects(self, doc) -> None:
        """订单保存后自动同步关联框架合同项目的 项目名称/部门 为订单最新值。

        框架合同项目行存的是创建时的快照，订单后续修改不会自动反映到合同项目列表，
        这里在订单更新时把项目的 项目名称/部门 同步为订单最新值；项目金额不覆盖（人工调整优先）。
        """
        from app.models.framework_contract import (
            FrameworkContractProject,
            FrameworkContractProjectDocument,
        )
        projects = (await self.db.execute(
            select(FrameworkContractProject)
            .join(
                FrameworkContractProjectDocument,
                FrameworkContractProjectDocument.project_id == FrameworkContractProject.id,
            )
            .where(
                FrameworkContractProjectDocument.document_id == doc.id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )).scalars().all()
        changed = False
        for p in projects:
            if (p.project_name or "") != (doc.project_name or ""):
                p.project_name = doc.project_name
                changed = True
            if (p.department or "") != (doc.department or ""):
                p.department = doc.department
                changed = True
        if changed:
            await self.db.flush()

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
        for link in links:
            await self.db.delete(link)

        # 3. 清理框架合同关联
        fw_links = (await self.db.execute(
            select(FrameworkContractProjectDocument).where(
                FrameworkContractProjectDocument.document_id == doc.id
            )
        )).scalars().all()
        for link in fw_links:
            await self.db.delete(link)

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
            "business_document_groups",
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
                    terminal_statuses=("confirmed", "completed"),
                )
            elif from_status == "in_production" and to_status == "in_installation":
                await self._require_all_tasks_completed(
                    doc_id, ProductionTask, "production_no", "生产"
                )
            elif from_status == "in_installation" and to_status == "completed":
                await self._require_all_tasks_completed(
                    doc_id, InstallationTask, "installation_no", "安装"
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
                "completed": "已完成",
                "cancelled": "已取消", "draft": "草稿", "converted": "已转换",
            }
            await notif_svc.create_system_notification(
                user_id=doc.sales_user_id,
                type_="order_status",
                title=f"单据状态变更: {doc.doc_no}",
                content=f"{doc.project_name} 状态从 {labels.get(from_status, from_status)} 变更为 {labels.get(to_status, to_status)}",
                link=f"/{'orders' if doc.doc_type == 'order' else 'quotes'}/{doc_id}",
            )

        # 状态更新使用数据库侧 onupdate 生成 updated_at。异步 SQLAlchemy 会将该
        # 字段标记为过期，序列化前必须显式异步刷新，否则同步读取会触发
        # MissingGreenlet 并让确认订单接口返回 500。
        await self.db.refresh(doc, attribute_names=["updated_at"])
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
        """管理员专用：将已完成订单退回安装中，供后续取消或纠正。"""
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("订单不存在")
        if doc.doc_type != "order" or doc.status != "completed":
            raise ValueError("只有已完成订单可以撤回")
        if not reason.strip():
            raise ValueError("撤回原因不能为空")
        await self.repo.update(doc, {"status": "in_installation"})
        await self.repo.create_status_log(doc_id, "completed", "in_installation", reason.strip(), operated_by)
        # 撤回后订单回到安装中，若无进行中的安装任务则新建一个，保证看板安装栏可跳转
        open_task = (await self.db.execute(
            select(InstallationTask).where(
                InstallationTask.document_id == doc_id,
                InstallationTask.status.not_in(["completed", "cancelled"]),
            )
        )).scalars().first()
        if not open_task:
            from app.services.number_generator import generate_installation_no
            task = InstallationTask(
                installation_no=await generate_installation_no(self.db),
                document_id=doc_id,
                customer_id=doc.customer_id,
                project_name=doc.project_name,
                status="pending",
            )
            self.db.add(task)
            await self.db.flush()
        return self._to_detail(doc)

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

    async def _auto_create_design_task(self, doc) -> None:
        from app.models.task import DesignTask
        from app.services.number_generator import generate_design_no

        active_items = [
            item for item in (doc.items or [])
            if getattr(item, "lifecycle_status", "active") == "active"
        ]
        if active_items:
            existing = await self.db.execute(
                select(DesignTask).where(DesignTask.document_id == doc.id)
            )
            existing_item_ids = {
                task.order_item_id
                for task in existing.scalars().all()
                if task.order_item_id is not None
                and task.status != "cancelled"
            }
            for item in active_items:
                if item.id in existing_item_ids:
                    continue
                self.db.add(DesignTask(
                    design_no=await generate_design_no(self.db),
                    document_id=doc.id,
                    order_item_id=item.id,
                    customer_id=doc.customer_id,
                    project_name=doc.project_name,
                    status="pending",
                ))
            await self.db.flush()
            return

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

        active_items = [
            item for item in (doc.items or [])
            if getattr(item, "lifecycle_status", "active") == "active"
        ]
        if active_items:
            existing = await self.db.execute(
                select(ProductionTask).where(ProductionTask.document_id == doc.id)
            )
            existing_item_ids = {
                task.order_item_id
                for task in existing.scalars().all()
                if task.order_item_id is not None
                and task.status != "cancelled"
            }
            for item in active_items:
                if item.id in existing_item_ids:
                    continue
                self.db.add(ProductionTask(
                    production_no=await generate_production_no(self.db),
                    document_id=doc.id,
                    order_item_id=item.id,
                    customer_id=doc.customer_id,
                    project_name=doc.project_name,
                    status="pending",
                    material_id=item.material_id,
                    process_id=item.process_id,
                    length=item.length,
                    width=item.width,
                    height=item.height,
                    quantity=item.quantity,
                ))
            await self.db.flush()
            return

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

        active_items = [
            item for item in (doc.items or [])
            if getattr(item, "lifecycle_status", "active") == "active"
        ]
        if active_items:
            existing = await self.db.execute(
                select(InstallationTask).where(InstallationTask.document_id == doc.id)
            )
            existing_item_ids = {
                task.order_item_id
                for task in existing.scalars().all()
                if task.order_item_id is not None
                and task.status != "cancelled"
            }
            for item in active_items:
                if item.id in existing_item_ids:
                    continue
                self.db.add(InstallationTask(
                    installation_no=await generate_installation_no(self.db),
                    document_id=doc.id,
                    order_item_id=item.id,
                    customer_id=doc.customer_id,
                    project_name=doc.project_name,
                    status="pending",
                    address=doc.installation_address,
                    contact_name=doc.contact_person,
                    contact_phone=doc.contact_phone,
                ))
            await self.db.flush()
            return

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

    async def update_order_contact(self, doc_id: UUID, contact_person: str | None, contact_phone: str | None) -> dict:
        """更新订单联系人（联系人独立填写，不再随报价单传递），保存时反向同步到客户管理。

        注意：repo.update 会跳过 None 值，清空联系人必须直接赋值属性。
        """
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise ValueError("单据不存在")
        if doc.doc_type != "order":
            raise ValueError("仅订单可设置联系人")
        contact_person = (contact_person or "").strip() or None
        contact_phone = (contact_phone or "").strip() or None
        doc.contact_person = contact_person
        doc.contact_phone = contact_phone
        await self.db.flush()
        await self._sync_contact_to_customer(doc, {
            "contact_person": contact_person,
            "contact_phone": contact_phone,
        })
        return self._to_detail(doc)

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
    # 核心：类型转换（报价 → 订单）
    # ═══════════════════════════════════════════

    async def convert_regular_quote_to_order(self, quote_id: UUID, created_by: UUID) -> dict:
        """常规报价转订单——新建订单并回链来源报价，保留报价历史（ADR-002）。

        与历史「同 ID 翻转」做法不同：创建新订单（全新 id、doc_no=O-xxx），
        原报价保留并置为 converted；订单 source_quote_id 指向报价，明细 source_quote_item_id 回链。
        """
        from app.models.business_document import BusinessDocument, BusinessDocumentItem
        from app.services.number_generator import generate_order_no

        result = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id == quote_id)
        )
        quote = result.scalar_one_or_none()
        if not quote or quote.doc_type != "quote" or quote.deleted_at is not None:
            raise ValueError("报价不存在")
        if quote.quote_mode != "regular":
            raise ValueError("仅常规报价支持此转换")

        # 幂等：已转换则返回现有订单
        if quote.status == "converted":
            existing = await self.db.execute(
                select(BusinessDocument).where(
                    BusinessDocument.source_quote_id == quote_id,
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.deleted_at.is_(None),
                ).order_by(BusinessDocument.created_at.desc()).limit(1)
            )
            e = existing.scalar_one_or_none()
            if e:
                return self._to_detail(e)
            raise ValueError("该报价已转订单，不能重复转换")
        if quote.status != "confirmed":
            raise ValueError("只有已确认的报价单可以转订单")

        # 补齐正式客户（自由输入客户的报价）
        await ensure_document_customer(self.db, quote, created_by)

        # 快照报价版本，保留转单前历史
        ver_no = await self.repo.get_next_version_no(quote_id)
        await self.repo.create_version(quote_id, ver_no, self._to_detail(quote), created_by)

        # 新建订单
        order_no = await generate_order_no(self.db)
        order = BusinessDocument(
            doc_type="order",
            doc_no=order_no,
            customer_id=quote.customer_id,
            customer_name=quote.customer_name,
            project_name=quote.project_name,
            sales_user_id=quote.sales_user_id,
            department=quote.department,
            contact_person=quote.contact_person,
            contact_phone=quote.contact_phone,
            status="pending_confirm",
            total_amount=quote.total_amount,
            paid_amount=0,
            unpaid_amount=quote.total_amount,
            cost_amount=0,
            gross_profit=quote.total_amount,
            source_quote_id=quote.id,
            remark=quote.remark,
        )
        self.db.add(order)
        await self.db.flush()

        # 复制明细（source_quote_item_id 回链原明细）
        # 注意：不要操作 order.items 关系——flush 后访问/赋值都会触发 selectin 懒加载
        # （异步 MissingGreenlet），改为直接以 document_id 关联入库，提交后由 refresh 统一加载
        for src in sorted(quote.items or [], key=lambda it: it.sort_order or 0):
            item = BusinessDocumentItem(
                document_id=order.id,
                source_quote_item_id=src.id,
                item_name=src.item_name,
                product_id=src.product_id,
                material_id=src.material_id,
                process_id=src.process_id,
                length=src.length,
                length_unit=src.length_unit,
                width=src.width,
                width_unit=src.width_unit,
                height=src.height,
                height_unit=src.height_unit,
                quantity=src.quantity,
                unit=src.unit,
                use_area=src.use_area,
                quantity_mode=src.quantity_mode,
                pieces=src.pieces,
                area=src.area,
                unit_price=src.unit_price,
                process_fee=src.process_fee,
                installation_fee=src.installation_fee,
                design_fee=src.design_fee,
                transport_fee=src.transport_fee,
                other_fee=src.other_fee,
                subtotal_amount=src.subtotal_amount,
                remark=src.remark,
                image_url=src.image_url,
                sort_order=src.sort_order,
                group_name=src.group_name,
                material_process=src.material_process,
            )
            self.db.add(item)

        # Copy group definitions too, including groups that currently have no details.
        from app.models.business_document import BusinessDocumentGroup
        for src_group in sorted(
            quote.groups or [],
            key=lambda group: (group.sort_order or 0, group.created_at),
        ):
            self.db.add(BusinessDocumentGroup(
                document_id=order.id,
                group_id=src_group.group_id,
                group_name=src_group.group_name,
                sort_order=src_group.sort_order,
            ))

        # 状态日志
        await self.repo.create_status_log(order.id, None, "pending_confirm", "来自常规报价转换", created_by)
        await self.repo.create_status_log(quote_id, quote.status, "converted", "已转为订单", created_by)

        # 报价状态 → converted
        quote.status = "converted"

        await self.db.commit()

        # 显式加载关系后再序列化（与 create() 的 refresh 模式一致），避免异步懒加载 MissingGreenlet
        await self.db.refresh(
            order,
            ["customer", "items", "groups", "status_logs", "design_tasks", "production_tasks", "installation_tasks"],
        )
        return self._to_detail(order)

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

    @staticmethod
    def _json_safe(value):
        """将 ORM/Decimal 值转换为可写入 JSONB 的审计值。"""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: BusinessDocumentService._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [BusinessDocumentService._json_safe(item) for item in value]
        return value

    @staticmethod
    def _to_decimal(value, default: str = "0") -> Decimal:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))

    @staticmethod
    def _to_order_item_input(item) -> dict:
        return {
            field: getattr(item, field, None)
            for field in ORDER_ITEM_FIELDS
        }

    @classmethod
    def _item_snapshot(cls, item) -> dict:
        snapshot = {
            "id": str(item.id),
            "source_quote_item_id": (
                str(item.source_quote_item_id)
                if getattr(item, "source_quote_item_id", None)
                else None
            ),
            **cls._to_order_item_input(item),
            "area": getattr(item, "area", None),
            "subtotal_amount": getattr(item, "subtotal_amount", None),
            "lifecycle_status": getattr(item, "lifecycle_status", "active"),
            "voided_at": getattr(item, "voided_at", None),
            "void_reason": getattr(item, "void_reason", None),
            "superseded_by_item_id": getattr(item, "superseded_by_item_id", None),
            "specification": _build_spec(item),
        }
        return cls._json_safe(snapshot)

    async def _count(self, statement) -> int:
        result = await self.db.execute(statement)
        return int(result.scalar() or 0)

    async def _sum_decimal(self, statement) -> Decimal:
        result = await self.db.execute(statement)
        return self._to_decimal(result.scalar())

    async def _get_nonvoided_payment_total(self, doc_id: UUID) -> Decimal:
        from app.models.payment import Payment

        return await self._sum_decimal(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.document_id == doc_id,
                Payment.is_voided.is_(False),
            )
        )

    @staticmethod
    def _relation_action(module: str, status: str | None) -> dict:
        """Return the safe action for one association in the confirmation catalog."""
        normalized_status = (status or "unknown").lower()
        if module == "outsource_tasks" and normalized_status in {"pending", "draft"}:
            return {
                "action": "refresh_plan",
                "risk": "medium",
                "fields": ["item_name", "quantity", "unit_price", "subtotal_amount"],
                "note": "未开始外协可按订单明细刷新计划值",
            }
        if module == "acceptance_forms" and normalized_status in {"draft", "pending", "rejected"}:
            return {
                "action": "refresh_draft",
                "risk": "medium",
                "fields": ["item_name", "quantity", "unit_price", "subtotal_amount"],
                "note": "草稿/待提交验收允许刷新明细快照",
            }
        if module in {"payments", "stock_records", "contracts", "framework_contracts", "customer_statements"}:
            return {
                "action": "preserve_fact_and_reconcile",
                "risk": "high",
                "fields": [],
                "note": "已发生事实不覆盖，变更后重新核对差额",
            }
        if module in {"cdr_quote_versions", "cdr_drawing_snapshots", "cdr_quote_geometry"}:
            return {
                "action": "preserve_fact_and_review",
                "risk": "high",
                "fields": [],
                "note": "来源报价的 CDR 版本/图稿/几何事实不由订单明细接口反写",
            }
        if module == "source_item_refs":
            return {
                "action": "preserve_fact_and_review",
                "risk": "high",
                "fields": [],
                "note": "该明细被其他明细作为来源引用，变更后必须人工核对引用快照",
            }
        if module == "acceptance_forms":
            return {
                "action": "preserve_fact_and_adjust",
                "risk": "high",
                "fields": [],
                "note": "已验收事实保留，差异进入调整/待复核",
            }
        if module == "outsource_tasks":
            return {
                "action": "preserve_fact_and_adjust",
                "risk": "high" if normalized_status in {"completed", "settled"} else "medium",
                "fields": [],
                "note": "已执行或已结算外协不覆盖历史金额",
            }
        if module in {"design_tasks", "production_tasks", "installation_tasks"}:
            if normalized_status in {"completed", "cancelled"}:
                return {
                    "action": "preserve_fact_and_review",
                    "risk": "high" if normalized_status == "completed" else "low",
                    "fields": [],
                    "note": "任务事实保留，订单明细差异待复核",
                }
            return {
                "action": "refresh_plan_or_review",
                "risk": "medium",
                "fields": ["project_name", "planned_quantity"],
                "note": "当前任务只有订单级关系，无法安全推断到某一明细",
            }
        if module == "project_costs":
            return {
                "action": "preserve_fact_and_review",
                "risk": "medium" if normalized_status != "settled" else "high",
                "fields": [],
                "note": "成本事实保留，明细变更后重新核对成本归属",
            }
        if module in {"vehicle_use_requests", "vehicle_dispatches", "vehicle_incidents", "vehicle_cost_allocations"}:
            return {
                "action": "preserve_fact_and_review",
                "risk": "high" if normalized_status in {"completed", "paid", "reimbursed"} else "medium",
                "fields": [],
                "note": "车辆计划/费用不由订单明细接口静默改写",
            }
        return {
            "action": "review_required",
            "risk": "high",
            "fields": [],
            "note": "关系无法稳定映射，禁止模糊刷新",
        }

    @staticmethod
    def _order_item_mutation_decision(
        doc,
        relations: dict,
        *,
        operation: str,
        after_total: Decimal,
        paid_amount: Decimal,
    ) -> dict:
        """Classify an order-item mutation without trusting frontend state."""
        lock_reasons: list[dict] = []
        if doc.status not in ORDER_ITEM_MUTABLE_STATUSES:
            lock_reasons.append({
                "code": "STATUS_LOCKED",
                "message": f"订单状态“{doc.status}”不允许修改明细",
            })
        if after_total < paid_amount:
            lock_reasons.append({
                "code": "PAID_EXCEEDS_TOTAL",
                "message": "变更后订单总额不能低于已收款金额",
            })

        task_counts = relations.get("tasks") or {}
        association_count = sum(
            int(relations.get(key) or 0)
            for key in (
                "payments",
                "acceptance_forms",
                "acceptance_item_refs",
                "source_item_refs",
                "outsource_tasks",
                "outsource_item_refs",
                "project_costs",
                "item_project_costs",
                "stock_out_records",
                "contract_links",
                "framework_contract_links",
                "vehicle_records",
                "confirmed_statements",
                "source_quote_refs",
                "cdr_records",
            )
        ) + int(task_counts.get("total") or 0)
        association_catalog = relations.get("association_catalog") or []
        has_associations = bool(association_count or association_catalog)
        high_risk = bool(
            relations.get("payments")
            or relations.get("accepted_acceptance_forms")
            or relations.get("stock_out_records")
            or relations.get("contract_links")
            or relations.get("framework_contract_links")
            or relations.get("confirmed_statements")
            or relations.get("source_item_refs")
            or any(
                entry.get("risk") == "high"
                for entry in association_catalog
                if isinstance(entry, dict)
            )
        )
        if has_associations and not settings.ORDER_ITEM_ASSOCIATED_EDIT_ENABLED:
            lock_reasons.append({
                "code": "ASSOCIATED_EDIT_FEATURE_DISABLED",
                "message": "执行中关联订单明细变更入口当前处于灰度关闭状态",
            })
        if lock_reasons:
            decision = "BLOCK"
        elif not has_associations:
            decision = "DIRECT_APPLY"
        elif high_risk:
            decision = "APPROVAL_AND_ADJUSTMENT"
        else:
            decision = "CONFIRM_AND_REFRESH"
        return {
            "decision": decision,
            "can_apply": not lock_reasons,
            "requires_confirmation": decision in {"CONFIRM_AND_REFRESH", "APPROVAL_AND_ADJUSTMENT"},
            "requires_high_risk_ack": decision == "APPROVAL_AND_ADJUSTMENT",
            "lock_reasons": lock_reasons,
            "association_count": association_count,
            "operation": operation,
        }

    @classmethod
    def _preview_signature_payload(
        cls,
        doc_id: UUID,
        operation: str,
        item_id: UUID | None,
        data: dict | None,
        reason: str,
        expected_updated_at: str | None,
        preview_id: str,
        preview_expires_at: str,
        context: dict,
        operated_by: UUID | None,
    ) -> dict:
        safe_context = cls._json_safe(context)
        if isinstance(safe_context, dict) and isinstance(safe_context.get("association_catalog"), list):
            safe_context["association_catalog"] = sorted(
                safe_context["association_catalog"],
                key=lambda entry: (
                    str(entry.get("module", "")),
                    str(entry.get("record_id", "")),
                    str(entry.get("record_no", "")),
                ),
            )
        return {
            "order_id": str(doc_id),
            "operation": operation,
            "item_id": str(item_id) if item_id else None,
            "data": cls._json_safe(data or {}),
            "reason": reason.strip(),
            "expected_updated_at": expected_updated_at,
            "preview_id": preview_id,
            "preview_expires_at": preview_expires_at,
            "operated_by": str(operated_by) if operated_by else None,
            "context": safe_context,
        }

    @classmethod
    def _make_preview_hash(cls, **kwargs) -> str:
        payload = cls._preview_signature_payload(**kwargs)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(_PREVIEW_SIGNING_SECRET, encoded, hashlib.sha256).hexdigest()

    @classmethod
    def _assert_preview_confirmation(
        cls,
        *,
        preview_id: str | None,
        plan_hash: str | None,
        preview_expires_at: str | None,
        doc_id: UUID,
        operation: str,
        item_id: UUID | None,
        data: dict | None,
        reason: str,
        expected_updated_at: str | None,
        operated_by: UUID | None,
        context: dict,
    ) -> None:
        if not preview_id or not plan_hash or not preview_expires_at:
            raise ValueError("请先完成影响预检并确认关联刷新")
        try:
            expires_at = datetime.fromisoformat(preview_expires_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("影响预检凭证格式无效，请重新预检") from exc
        now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.now()
        if expires_at <= now:
            raise ValueError("影响预检已过期，请重新预检")
        expected_hash = cls._make_preview_hash(
            doc_id=doc_id,
            operation=operation,
            item_id=item_id,
            data=data,
            reason=reason,
            expected_updated_at=expected_updated_at,
            preview_id=preview_id,
            preview_expires_at=preview_expires_at,
            context=context,
            operated_by=operated_by,
        )
        if not hmac.compare_digest(expected_hash, plan_hash):
            raise ValueError("影响目录已变化，请重新预检后确认")

    async def _find_applied_mutation(self, doc_id: UUID, change_batch_id: str | None):
        if not change_batch_id:
            return None
        from app.models.business_document import BusinessDocumentVersion

        result = await self.db.execute(
            select(BusinessDocumentVersion)
            .where(BusinessDocumentVersion.document_id == doc_id)
            .order_by(BusinessDocumentVersion.created_at.desc())
        )
        for version in result.scalars().all():
            snapshot = version.snapshot or {}
            if (
                isinstance(snapshot, dict)
                and snapshot.get("change_batch_id") == change_batch_id
                and snapshot.get("change_status") in {
                    "APPLIED",
                    "VERIFIED",
                    "PENDING_ADJUSTMENT",
                }
            ):
                return snapshot
        return None

    async def _collect_order_item_relation_catalog(
        self,
        doc,
        *,
        item_id: UUID | None = None,
    ) -> list[dict]:
        """Return record-level relations for the confirmation dialog.

        The catalog intentionally exposes only stable foreign-key/document links.
        Project/customer text matches are never used as a fallback relation.
        """
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.models.business_document import BusinessDocument, BusinessDocumentItem
        from app.models.contract import Contract, ContractDocument
        from app.models.framework_contract import (
            FrameworkContractProject,
            FrameworkContractProjectDocument,
        )
        from app.models.inventory import StockRecord
        from app.models.outsource import OutsourceTask
        from app.models.payment import CustomerStatement, Payment
        from app.models.project_cost import ProjectCost
        from app.models.task import DesignTask, InstallationTask, ProductionTask
        from app.models.vehicle import (
            VehicleCostAllocation,
            VehicleDispatch,
            VehicleIncident,
            VehicleUseRequest,
        )
        from app.models.cdr_quote import DrawingSnapshot, QuoteGeometry, QuoteVersion

        catalog: list[dict] = []

        def add_entry(
            module: str,
            label: str,
            record,
            *,
            record_no: str | None,
            status: str | None,
            relation_type: str,
        ) -> None:
            action = self._relation_action(module, status)
            catalog.append({
                "module": module,
                "label": label,
                "relation_type": relation_type,
                "record_id": str(record.id),
                "record_no": record_no,
                "status": status,
                **action,
            })

        task_models = (
            (DesignTask, "design_tasks", "设计任务", "design_no"),
            (ProductionTask, "production_tasks", "生产任务", "production_no"),
            (InstallationTask, "installation_tasks", "安装任务", "installation_no"),
        )
        for model, module, label, no_field in task_models:
            result = await self.db.execute(
                select(model)
                .where(model.document_id == doc.id)
                .order_by(model.updated_at.desc())
            )
            for record in result.scalars().all():
                add_entry(
                    module,
                    label,
                    record,
                    record_no=getattr(record, no_field, None),
                    status=record.status,
                    relation_type="document",
                )

        form_result = await self.db.execute(
            select(AcceptanceForm)
            .where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
            .order_by(AcceptanceForm.updated_at.desc())
        )
        forms = form_result.scalars().all()
        for form in forms:
            add_entry(
                "acceptance_forms",
                "验收单",
                form,
                record_no=form.acceptance_no,
                status=form.status,
                relation_type="document",
            )
        if item_id:
            item_result = await self.db.execute(
                select(AcceptanceItem, AcceptanceForm)
                .join(AcceptanceForm, AcceptanceForm.id == AcceptanceItem.acceptance_id)
                .where(
                    AcceptanceForm.document_id == doc.id,
                    AcceptanceForm.deleted_at.is_(None),
                    AcceptanceItem.document_item_id == item_id,
                )
            )
            for acceptance_item, form in item_result.all():
                add_entry(
                    "acceptance_items",
                    "验收明细",
                    acceptance_item,
                    record_no=form.acceptance_no,
                    status=acceptance_item.item_status,
                    relation_type="item",
                )

        outsource_query = select(OutsourceTask).where(
            OutsourceTask.related_doc_id == doc.id,
            OutsourceTask.related_doc_type == "order",
        )
        if item_id:
            outsource_query = outsource_query.where(
                or_(
                    OutsourceTask.order_item_id == item_id,
                    OutsourceTask.order_item_id.is_(None),
                )
            )
        outsource_result = await self.db.execute(
            outsource_query.order_by(OutsourceTask.updated_at.desc())
        )
        for record in outsource_result.scalars().all():
            add_entry(
                "outsource_tasks",
                "外协任务",
                record,
                record_no=record.task_no,
                status=record.status,
                relation_type="item" if record.order_item_id else "document",
            )

        cost_query = select(ProjectCost).where(
            or_(
                ProjectCost.document_id == doc.id,
                ProjectCost.document_item_id.in_(
                    select(BusinessDocumentItem.id).where(
                        BusinessDocumentItem.document_id == doc.id,
                    )
                ),
            )
        )
        if item_id:
            cost_query = select(ProjectCost).where(
                or_(
                    ProjectCost.document_id == doc.id,
                    ProjectCost.document_item_id == item_id,
                )
            )
        cost_result = await self.db.execute(cost_query.order_by(ProjectCost.updated_at.desc()))
        for record in cost_result.scalars().all():
            add_entry(
                "project_costs",
                "项目成本",
                record,
                record_no=record.cost_no,
                status="settled" if record.is_settled else "active",
                relation_type="item" if record.document_item_id else "document",
            )

        simple_models = (
            (StockRecord, "stock_records", "库存记录", None, "record_type"),
            (Payment, "payments", "收款记录", "payment_no", None),
        )
        for model, module, label, no_field, status_field in simple_models:
            query = select(model).where(model.document_id == doc.id)
            if model is Payment:
                query = query.where(Payment.is_voided.is_(False))
            result = await self.db.execute(query.order_by(model.updated_at.desc()))
            for record in result.scalars().all():
                status = (
                    "active" if model is Payment and not record.is_voided
                    else getattr(record, status_field, None) if status_field
                    else None
                )
                add_entry(
                    module,
                    label,
                    record,
                    record_no=getattr(record, no_field, None) if no_field else None,
                    status=status,
                    relation_type="document",
                )

        contract_result = await self.db.execute(
            select(Contract, ContractDocument)
            .join(ContractDocument, ContractDocument.contract_id == Contract.id)
            .where(ContractDocument.document_id == doc.id)
            .order_by(Contract.updated_at.desc())
        )
        for contract, _ in contract_result.all():
            add_entry(
                "contracts",
                "合同",
                contract,
                record_no=contract.contract_no,
                status=contract.status,
                relation_type="document",
            )

        framework_result = await self.db.execute(
            select(FrameworkContractProject, FrameworkContractProjectDocument)
            .join(
                FrameworkContractProjectDocument,
                FrameworkContractProjectDocument.project_id == FrameworkContractProject.id,
            )
            .where(FrameworkContractProjectDocument.document_id == doc.id)
            .order_by(FrameworkContractProject.updated_at.desc())
        )
        for project, _ in framework_result.all():
            add_entry(
                "framework_contracts",
                "框架合同项目",
                project,
                record_no=str(project.id),
                status="deleted" if project.deleted_at else "active",
                relation_type="document",
            )

        vehicle_models = (
            (VehicleUseRequest, "vehicle_use_requests", "用车申请", "request_no"),
            (VehicleDispatch, "vehicle_dispatches", "派车单", "dispatch_no"),
            (VehicleIncident, "vehicle_incidents", "车辆事件", None),
            (VehicleCostAllocation, "vehicle_cost_allocations", "车辆费用分摊", None),
        )
        for model, module, label, no_field in vehicle_models:
            result = await self.db.execute(
                select(model)
                .where(model.related_order_id == doc.id)
                .order_by(model.updated_at.desc())
            )
            for record in result.scalars().all():
                add_entry(
                    module,
                    label,
                    record,
                    record_no=getattr(record, no_field, None) if no_field else None,
                    status=getattr(record, "status", None),
                    relation_type="document",
                )

        if doc.created_at and doc.customer_id:
            statement_result = await self.db.execute(
                select(CustomerStatement).where(
                    CustomerStatement.customer_id == doc.customer_id,
                    CustomerStatement.status == "confirmed",
                    CustomerStatement.start_date <= doc.created_at,
                    CustomerStatement.end_date >= doc.created_at,
                )
            )
            for record in statement_result.scalars().all():
                add_entry(
                    "customer_statements",
                    "客户对账单",
                    record,
                    record_no=record.statement_no,
                    status=record.status,
                    relation_type="snapshot",
                )

        if doc.source_quote_id:
            cdr_models = (
                (QuoteVersion, "cdr_quote_versions", "来源报价版本"),
                (DrawingSnapshot, "cdr_drawing_snapshots", "CDR 图稿快照"),
                (QuoteGeometry, "cdr_quote_geometry", "CDR 几何分析"),
            )
            for model, module, label in cdr_models:
                result = await self.db.execute(
                    select(model)
                    .where(model.quote_id == doc.source_quote_id)
                    .order_by(model.updated_at.desc())
                )
                for record in result.scalars().all():
                    if module == "cdr_quote_versions":
                        record_no = f"{doc.source_quote_id}:v{record.version_no}"
                        status = record.status
                    elif module == "cdr_drawing_snapshots":
                        record_no = record.snapshot_code
                        status = "frozen"
                    else:
                        record_no = str(record.id)
                        status = "analyzed"
                    add_entry(
                        module,
                        label,
                        record,
                        record_no=record_no,
                        status=status,
                        relation_type="source",
                    )
            source_result = await self.db.execute(
                select(BusinessDocument).where(BusinessDocument.id == doc.source_quote_id)
            )
            source_quote = source_result.scalar_one_or_none()
            if source_quote:
                add_entry(
                    "source_quote",
                    "来源报价单",
                    source_quote,
                    record_no=source_quote.doc_no,
                    status=source_quote.status,
                    relation_type="source",
                )
        if item_id:
            source_item_result = await self.db.execute(
                select(BusinessDocumentItem).where(
                    BusinessDocumentItem.source_quote_item_id == item_id
                )
            )
            for record in source_item_result.scalars().all():
                add_entry(
                    "source_item_refs",
                    "来源明细引用",
                    record,
                    record_no=str(record.id),
                    status=getattr(record, "lifecycle_status", "active"),
                    relation_type="item",
                )
        return sorted(
            catalog,
            key=lambda entry: (
                str(entry.get("module", "")),
                str(entry.get("record_id", "")),
            ),
        )

    async def _collect_order_item_relations(
        self,
        doc,
        *,
        item_id: UUID | None = None,
    ) -> dict:
        """收集明细编辑的关联影响。

        这里故意同时检查带软删除标记的历史引用：部分表对明细使用 NO ACTION
        外键，或者没有外键（如 outsource_tasks.order_item_id），不能只依赖 ORM
        relationship 或数据库约束判断是否安全。
        """
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.models.business_document import BusinessDocumentItem
        from app.models.contract import ContractDocument
        from app.models.framework_contract import FrameworkContractProjectDocument
        from app.models.inventory import StockRecord
        from app.models.outsource import OutsourceTask
        from app.models.payment import CustomerStatement, Payment
        from app.models.project_cost import ProjectCost
        from app.models.task import DesignTask, InstallationTask, ProductionTask
        from app.models.vehicle import (
            VehicleCostAllocation,
            VehicleDispatch,
            VehicleIncident,
            VehicleUseRequest,
        )

        active_acceptance = {
            "forms": await self._count(
                select(func.count(AcceptanceForm.id)).where(
                    AcceptanceForm.document_id == doc.id,
                    AcceptanceForm.deleted_at.is_(None),
                )
            ),
            "accepted_forms": await self._count(
                select(func.count(AcceptanceForm.id)).where(
                    AcceptanceForm.document_id == doc.id,
                    AcceptanceForm.deleted_at.is_(None),
                    AcceptanceForm.status == "accepted",
                )
            ),
            # 不带 deleted_at 条件，用于阻止明细物理删除触发 NO ACTION FK。
            "item_refs": await self._count(
                select(func.count(AcceptanceItem.id))
                .join(AcceptanceForm, AcceptanceForm.id == AcceptanceItem.acceptance_id)
                .where(
                    AcceptanceForm.document_id == doc.id,
                    AcceptanceItem.document_item_id.isnot(None),
                    *(
                        [AcceptanceItem.document_item_id == item_id]
                        if item_id
                        else []
                    ),
                )
            ),
        }

        task_counts = {
            "design": await self._count(
                select(func.count(DesignTask.id)).where(
                    DesignTask.document_id == doc.id,
                    DesignTask.status != "cancelled",
                )
            ),
            "production": await self._count(
                select(func.count(ProductionTask.id)).where(
                    ProductionTask.document_id == doc.id,
                    ProductionTask.status != "cancelled",
                )
            ),
            "installation": await self._count(
                select(func.count(InstallationTask.id)).where(
                    InstallationTask.document_id == doc.id,
                    InstallationTask.status != "cancelled",
                )
            ),
        }
        task_counts["total"] = sum(task_counts.values())

        relations = {
            "payments": await self._count(
                select(func.count(Payment.id)).where(
                    Payment.document_id == doc.id,
                    Payment.is_voided.is_(False),
                )
            ),
            "acceptance_forms": active_acceptance["forms"],
            "accepted_acceptance_forms": active_acceptance["accepted_forms"],
            "acceptance_item_refs": active_acceptance["item_refs"],
            # source_quote_item_id 是自引用 FK；虽然正常订单不会作为来源，仍需
            # 防止历史数据或异常转换留下子明细后直接删除父明细。
            "source_item_refs": await self._count(
                select(func.count(BusinessDocumentItem.id)).where(
                    BusinessDocumentItem.source_quote_item_id == item_id
                    if item_id
                    else False,
                )
            ),
            "tasks": task_counts,
            "outsource_tasks": await self._count(
                select(func.count(OutsourceTask.id)).where(
                    OutsourceTask.related_doc_id == doc.id,
                    OutsourceTask.related_doc_type == "order",
                    OutsourceTask.deleted_at.is_(None),
                )
            ),
            # 没有 FK，包含历史软删除任务，避免留下悬空明细引用。
            "outsource_item_refs": await self._count(
                select(func.count(OutsourceTask.id)).where(
                    OutsourceTask.related_doc_id == doc.id,
                    OutsourceTask.related_doc_type == "order",
                    OutsourceTask.order_item_id.isnot(None),
                    *(
                        [OutsourceTask.order_item_id == item_id]
                        if item_id
                        else []
                    ),
                )
            ),
            "project_costs": await self._count(
                select(func.count(ProjectCost.id)).where(
                    ProjectCost.document_id == doc.id,
                    ProjectCost.deleted_at.is_(None),
                )
            ),
            # SET NULL 仍会丢失明细维度的成本解释，因此单独阻断。
            "item_project_costs": await self._count(
                select(func.count(ProjectCost.id)).where(
                    ProjectCost.document_item_id == item_id
                    if item_id
                    else ProjectCost.document_id == doc.id,
                )
            ),
            "stock_out_records": await self._count(
                select(func.count(StockRecord.id)).where(
                    StockRecord.document_id == doc.id,
                    StockRecord.record_type == "out",
                )
            ),
            "contract_links": await self._count(
                select(func.count(ContractDocument.id)).where(
                    ContractDocument.document_id == doc.id,
                )
            ),
            "framework_contract_links": await self._count(
                select(func.count(FrameworkContractProjectDocument.id)).where(
                    FrameworkContractProjectDocument.document_id == doc.id,
                )
            ),
            "vehicle_records": 0,
            "confirmed_statements": 0,
            "source_quote_refs": 1 if doc.source_quote_id else 0,
            "cdr_records": 0,
        }

        for model in (
            VehicleUseRequest,
            VehicleDispatch,
            VehicleIncident,
            VehicleCostAllocation,
        ):
            relations["vehicle_records"] += await self._count(
                select(func.count(model.id)).where(model.related_order_id == doc.id)
            )

        # 对账单是区间快照，没有订单明细关联表，只能识别可能覆盖该订单创建时间的
        # 已确认对账单，并在预检结果中标记为需要人工复核。
        if doc.created_at:
            relations["confirmed_statements"] = await self._count(
                select(func.count(CustomerStatement.id)).where(
                    CustomerStatement.customer_id == doc.customer_id,
                    CustomerStatement.status == "confirmed",
                    CustomerStatement.start_date <= doc.created_at,
                    CustomerStatement.end_date >= doc.created_at,
                )
            )
        if doc.source_quote_id:
            from app.models.cdr_quote import DrawingSnapshot, QuoteGeometry, QuoteVersion

            for model in (QuoteVersion, DrawingSnapshot, QuoteGeometry):
                relations["cdr_records"] += await self._count(
                    select(func.count(model.id)).where(
                        model.quote_id == doc.source_quote_id
                    )
                )
        relations["association_catalog"] = await self._collect_order_item_relation_catalog(
            doc,
            item_id=item_id,
        )
        return relations

    @staticmethod
    def _order_item_lock_reasons(doc, relations: dict) -> list[dict]:
        reasons = []

        def add(code: str, message: str) -> None:
            reasons.append({"code": code, "message": message})

        if doc.status not in ORDER_ITEM_MUTABLE_STATUSES:
            add("STATUS_LOCKED", f"订单状态“{doc.status}”不允许直接修改明细")
        if relations["payments"]:
            add("PAYMENT_LINKED", "订单已有未作废收款，明细直接变更会影响应收核对")
        if relations["accepted_acceptance_forms"]:
            add("ACCEPTANCE_ACCEPTED", "订单已有已验收单，不能直接覆盖验收事实")
        elif relations["acceptance_forms"] or relations["acceptance_item_refs"]:
            add("ACCEPTANCE_LINKED", "订单已有验收关联，不能静默改变验收快照")
        if relations["source_item_refs"]:
            add("SOURCE_ITEM_LINKED", "该明细被其他单据明细作为来源引用，不能直接覆盖或删除")
        if relations["tasks"]["total"]:
            add("TASK_LINKED", "订单已有执行任务，需要通过变更流程复核任务内容")
        if relations["outsource_tasks"] or relations["outsource_item_refs"]:
            add("OUTSOURCE_LINKED", "订单已有外协任务或明细引用，不能直接改变执行范围")
        if relations["project_costs"] or relations["item_project_costs"]:
            add("COST_LINKED", "订单已有项目成本，不能让成本与明细关系无痕断开")
        if relations["stock_out_records"]:
            add("STOCK_OUT_LINKED", "订单已有库存出库记录，需要库存调整流程")
        if relations["vehicle_records"]:
            add("VEHICLE_LINKED", "订单已有车辆申请、派车或费用关联，需要车辆计划复核")
        if relations["contract_links"]:
            add("CONTRACT_LINKED", "订单已关联合同，金额变更需要合同变更或审批")
        if relations["framework_contract_links"]:
            add("FRAMEWORK_CONTRACT_LINKED", "订单已关联框架合同项目，项目金额需要单独复核")
        if relations["confirmed_statements"]:
            add("STATEMENT_CONFIRMED", "订单可能已包含在已确认客户对账单中")
        return reasons

    @staticmethod
    def _version_value(doc) -> str | None:
        updated_at = getattr(doc, "updated_at", None)
        return updated_at.isoformat() if updated_at else None

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        from datetime import timezone

        if value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @classmethod
    def _assert_expected_updated_at(cls, doc, expected_updated_at: str | None) -> None:
        if not expected_updated_at:
            return
        try:
            expected = cls._normalize_datetime(datetime.fromisoformat(expected_updated_at.replace("Z", "+00:00")))
        except ValueError as exc:
            raise ValueError("订单版本格式无效，请刷新订单后重试") from exc
        actual_value = getattr(doc, "updated_at", None)
        if not actual_value:
            raise OrderItemMutationConflict("订单版本已变化，请刷新订单后重试")
        actual = cls._normalize_datetime(actual_value)
        if actual != expected:
            raise OrderItemMutationConflict("订单已被其他人修改，请刷新订单后重试")

    async def _get_locked_order(self, doc_id: UUID):
        result = await self.db.execute(
            select(BusinessDocument.id)
            .where(
                BusinessDocument.id == doc_id,
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if result.scalar_one_or_none() is None:
            return None
        return await self.repo.get_by_id(doc_id)

    async def get_order_item_editability(self, doc_id: UUID) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "order":
            raise ValueError("订单不存在")
        relations = await self._collect_order_item_relations(doc)
        items = await self.repo.get_items(doc.id)
        total = sum(
            (self._to_decimal(item.subtotal_amount) for item in items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        paid = await self._get_nonvoided_payment_total(doc.id)
        decision = self._order_item_mutation_decision(
            doc,
            relations,
            operation="update",
            after_total=total,
            paid_amount=paid,
        )
        return {
            "order_id": str(doc.id),
            "order_no": doc.doc_no,
            "status": doc.status,
            "updated_at": self._version_value(doc),
            "can_edit_items": decision["can_apply"],
            "associated_edit_enabled": settings.ORDER_ITEM_ASSOCIATED_EDIT_ENABLED,
            "editable_statuses": sorted(ORDER_ITEM_MUTABLE_STATUSES),
            "decision": decision["decision"],
            "requires_confirmation": decision["requires_confirmation"],
            "requires_high_risk_ack": decision["requires_high_risk_ack"],
            "association_count": decision["association_count"],
            "lock_reasons": decision["lock_reasons"],
            "association_catalog": self._json_safe(relations.get("association_catalog") or []),
            "relations": self._json_safe(relations),
        }

    @staticmethod
    def _change_batch_summary(version) -> dict | None:
        snapshot = version.snapshot or {}
        if not isinstance(snapshot, dict) or not snapshot.get("change_batch_id"):
            return None
        raw_refresh_result = snapshot.get("refresh_result")
        refresh_result = raw_refresh_result if isinstance(raw_refresh_result, dict) else {}
        counts = refresh_result.get("counts") if isinstance(refresh_result, dict) else {}
        return {
            "change_batch_id": snapshot.get("change_batch_id"),
            "version_id": str(version.id),
            "version_no": version.version_no,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "created_by": str(version.created_by) if version.created_by else None,
            "operator_id": snapshot.get("operator_id"),
            "change_type": snapshot.get("change_type"),
            "reason": snapshot.get("reason"),
            "status": snapshot.get("change_status", "UNKNOWN"),
            "status_history": snapshot.get("status_history") or [],
            "verification_status": snapshot.get("verification_status", "UNKNOWN"),
            "counts": counts,
            "before": snapshot.get("before"),
            "after": snapshot.get("after"),
            "impact": snapshot.get("impact"),
            "refresh_result": raw_refresh_result,
        }

    async def list_order_item_change_batches(
        self,
        doc_id: UUID,
        *,
        limit: int = 50,
        change_batch_id: str | None = None,
    ) -> dict:
        """List immutable order-item change batches and their verification results."""
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "order":
            raise ValueError("订单不存在")

        from app.models.business_document import BusinessDocumentVersion

        result = await self.db.execute(
            select(BusinessDocumentVersion)
            .where(BusinessDocumentVersion.document_id == doc.id)
            .order_by(BusinessDocumentVersion.created_at.desc())
        )
        batches = []
        matched = 0
        batch_limit = max(1, min(limit, 200))
        for version in result.scalars().all():
            batch = self._change_batch_summary(version)
            if not batch:
                continue
            if change_batch_id and batch["change_batch_id"] != change_batch_id:
                continue
            matched += 1
            if change_batch_id or len(batches) < batch_limit:
                batches.append(batch)
        return {
            "order_id": str(doc.id),
            "order_no": doc.doc_no,
            "total": matched,
            "batches": self._json_safe(batches),
        }

    async def get_order_item_change_batch(
        self,
        doc_id: UUID,
        change_batch_id: str,
    ) -> dict:
        result = await self.list_order_item_change_batches(
            doc_id,
            limit=200,
            change_batch_id=change_batch_id,
        )
        if not result["batches"]:
            raise ValueError("变更批次不存在或不属于当前订单")
        return result["batches"][0]

    async def reconcile_order_item_change(
        self,
        doc_id: UUID,
        *,
        change_batch_id: str | None = None,
    ) -> dict:
        """Run a read-only order-wide reconciliation over current and historical facts.

        The checks use stable document/item foreign keys only. Order-level task,
        stock, vehicle, contract and statement links are reported as reviewable
        associations; they are never assigned to a line by project/customer text.
        """
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "order":
            raise ValueError("订单不存在")

        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.models.business_document import BusinessDocumentItem
        from app.models.contract import Contract, ContractDocument
        from app.models.framework_contract import (
            FrameworkContractProject,
            FrameworkContractProjectDocument,
        )
        from app.models.inventory import StockRecord
        from app.models.outsource import OutsourceTask
        from app.models.payment import CustomerStatement, Payment
        from app.models.project_cost import ProjectCost
        from app.models.task import DesignTask, InstallationTask, ProductionTask
        from app.models.vehicle import (
            VehicleCostAllocation,
            VehicleDispatch,
            VehicleIncident,
            VehicleUseRequest,
        )
        from app.models.cdr_quote import DrawingSnapshot, QuoteGeometry, QuoteVersion

        active_items = await self.repo.get_items(doc.id)
        all_item_result = await self.db.execute(
            select(BusinessDocumentItem.id, BusinessDocumentItem.lifecycle_status)
            .where(BusinessDocumentItem.document_id == doc.id)
        )
        all_item_rows = all_item_result.all()
        all_item_ids = {row[0] for row in all_item_rows}
        active_item_ids = {
            row[0] for row in all_item_rows if row[1] == "active"
        }

        active_item_total = sum(
            (self._to_decimal(item.subtotal_amount) for item in active_items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        payment_total = await self._get_nonvoided_payment_total(doc.id)
        payment_count = await self._count(
            select(func.count(Payment.id)).where(
                Payment.document_id == doc.id,
                Payment.is_voided.is_(False),
            )
        )

        cost_filter = [ProjectCost.deleted_at.is_(None)]
        cost_filter.append(
            or_(
                ProjectCost.document_id == doc.id,
                ProjectCost.document_item_id.in_(all_item_ids),
            )
        )
        cost_total = await self._sum_decimal(
            select(func.coalesce(func.sum(ProjectCost.amount), 0)).where(*cost_filter)
        )
        cost_count = await self._count(
            select(func.count(ProjectCost.id)).where(*cost_filter)
        )

        task_models = (
            (DesignTask, "design_tasks"),
            (ProductionTask, "production_tasks"),
            (InstallationTask, "installation_tasks"),
        )
        task_summary = {}
        for model, module in task_models:
            task_result = await self.db.execute(
                select(model).where(model.document_id == doc.id)
            )
            rows = task_result.scalars().all()
            task_summary[module] = {
                "total": len(rows),
                "active": sum(row.status != "cancelled" for row in rows),
                "completed": sum(row.status == "completed" for row in rows),
                "cancelled": sum(row.status == "cancelled" for row in rows),
                "mapping": "document_level_only",
            }
            if model is ProductionTask:
                task_summary[module]["planned_quantity"] = self._json_safe(
                    sum(
                        (
                            self._to_decimal(row.quantity)
                            for row in rows
                            if row.status != "cancelled"
                        ),
                        Decimal("0"),
                    )
                )

        form_result = await self.db.execute(
            select(AcceptanceForm).where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )
        forms = form_result.scalars().all()
        acceptance_item_result = await self.db.execute(
            select(AcceptanceItem, AcceptanceForm)
            .join(AcceptanceForm, AcceptanceForm.id == AcceptanceItem.acceptance_id)
            .where(
                AcceptanceForm.document_id == doc.id,
                AcceptanceForm.deleted_at.is_(None),
            )
        )
        acceptance_rows = acceptance_item_result.all()

        outsource_result = await self.db.execute(
            select(OutsourceTask).where(
                OutsourceTask.related_doc_id == doc.id,
                OutsourceTask.related_doc_type == "order",
                OutsourceTask.deleted_at.is_(None),
            )
        )
        outsource_rows = outsource_result.scalars().all()

        stock_result = await self.db.execute(
            select(StockRecord).where(StockRecord.document_id == doc.id)
        )
        stock_rows = stock_result.scalars().all()

        contract_result = await self.db.execute(
            select(Contract)
            .join(ContractDocument, ContractDocument.contract_id == Contract.id)
            .where(
                ContractDocument.document_id == doc.id,
                Contract.deleted_at.is_(None),
            )
        )
        contract_rows = list({
            row.id: row for row in contract_result.scalars().all()
        }.values())

        framework_result = await self.db.execute(
            select(FrameworkContractProject)
            .join(
                FrameworkContractProjectDocument,
                FrameworkContractProjectDocument.project_id == FrameworkContractProject.id,
            )
            .where(
                FrameworkContractProjectDocument.document_id == doc.id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )
        framework_rows = list({
            row.id: row for row in framework_result.scalars().all()
        }.values())

        vehicle_models = (
            (VehicleUseRequest, "vehicle_use_requests"),
            (VehicleDispatch, "vehicle_dispatches"),
            (VehicleIncident, "vehicle_incidents"),
            (VehicleCostAllocation, "vehicle_cost_allocations"),
        )
        vehicle_summary = {}
        for model, module in vehicle_models:
            vehicle_summary[module] = await self._count(
                select(func.count(model.id)).where(model.related_order_id == doc.id)
            )

        confirmed_statement_count = 0
        if doc.created_at and doc.customer_id:
            confirmed_statement_count = await self._count(
                select(func.count(CustomerStatement.id)).where(
                    CustomerStatement.customer_id == doc.customer_id,
                    CustomerStatement.status == "confirmed",
                    CustomerStatement.start_date <= doc.created_at,
                    CustomerStatement.end_date >= doc.created_at,
                )
            )

        cdr_summary = {
            "quote_id": str(doc.source_quote_id) if doc.source_quote_id else None,
            "versions": 0,
            "drawing_snapshots": 0,
            "geometry_records": 0,
            "mapping": "source_quote_id_only",
        }
        if doc.source_quote_id:
            for model, key in (
                (QuoteVersion, "versions"),
                (DrawingSnapshot, "drawing_snapshots"),
                (QuoteGeometry, "geometry_records"),
            ):
                cdr_summary[key] = await self._count(
                    select(func.count(model.id)).where(
                        model.quote_id == doc.source_quote_id
                    )
                )

        orphan_references = []

        def record_orphan(module: str, record, referenced_item_id, record_no=None):
            orphan_references.append({
                "module": module,
                "record_id": str(record.id),
                "record_no": record_no,
                "referenced_item_id": str(referenced_item_id),
                "reason": "明细引用不存在于当前订单，禁止自动刷新",
            })

        for acceptance_item, form in acceptance_rows:
            if acceptance_item.document_item_id and acceptance_item.document_item_id not in all_item_ids:
                record_orphan(
                    "acceptance_items",
                    acceptance_item,
                    acceptance_item.document_item_id,
                    form.acceptance_no,
                )
        for task in outsource_rows:
            if task.order_item_id and task.order_item_id not in all_item_ids:
                record_orphan(
                    "outsource_tasks",
                    task,
                    task.order_item_id,
                    task.task_no,
                )
        cost_result = await self.db.execute(
            select(ProjectCost).where(*cost_filter)
        )
        for cost in cost_result.scalars().all():
            if cost.document_item_id and cost.document_item_id not in all_item_ids:
                record_orphan(
                    "project_costs",
                    cost,
                    cost.document_item_id,
                    cost.cost_no,
                )

        parent_total = self._to_decimal(doc.total_amount).quantize(MONEY_QUANTUM)
        parent_paid = self._to_decimal(doc.paid_amount).quantize(MONEY_QUANTUM)
        parent_unpaid = self._to_decimal(doc.unpaid_amount).quantize(MONEY_QUANTUM)
        parent_cost = self._to_decimal(doc.cost_amount).quantize(MONEY_QUANTUM)
        parent_profit = self._to_decimal(doc.gross_profit).quantize(MONEY_QUANTUM)
        expected_unpaid = (parent_total - payment_total).quantize(MONEY_QUANTUM)
        expected_profit = (parent_total - parent_cost).quantize(MONEY_QUANTUM)
        checks = {
            "order_total_equals_active_items": {
                "ok": parent_total == active_item_total,
                "actual": parent_total,
                "expected": active_item_total,
            },
            "paid_equals_non_voided_payments": {
                "ok": parent_paid == payment_total,
                "actual": parent_paid,
                "expected": payment_total,
            },
            "unpaid_formula": {
                "ok": parent_unpaid == expected_unpaid and parent_unpaid >= 0,
                "actual": parent_unpaid,
                "expected": expected_unpaid,
            },
            "gross_profit_formula": {
                "ok": parent_profit == expected_profit,
                "actual": parent_profit,
                "expected": expected_profit,
            },
            "no_orphan_item_references": {
                "ok": not orphan_references,
                "actual": len(orphan_references),
                "expected": 0,
            },
        }

        batch = None
        if change_batch_id:
            batch = await self.get_order_item_change_batch(doc.id, change_batch_id)
        history_check = {
            "ok": True,
            "active_item_count": len(active_item_ids),
            "voided_or_superseded_item_count": max(len(all_item_ids) - len(active_item_ids), 0),
            "batch_id": change_batch_id,
        }
        if batch:
            history_check["ok"] = bool(
                batch.get("before")
                and batch.get("after")
                and batch.get("refresh_result") is not None
            )
            checks["change_batch_history_complete"] = history_check
            checks["change_batch_fully_verified"] = {
                "ok": batch.get("status") == "VERIFIED",
                "actual": batch.get("status"),
                "expected": "VERIFIED",
            }

        core_ok = all(check["ok"] for check in checks.values())
        return self._json_safe({
            "order_id": str(doc.id),
            "order_no": doc.doc_no,
            "checked_at": datetime.now().isoformat(),
            "status": "PASS" if core_ok else "ATTENTION",
            "checks": checks,
            "financials": {
                "active_item_total": active_item_total,
                "order_total": parent_total,
                "payment_total": payment_total,
                "payment_count": payment_count,
                "order_paid_amount": parent_paid,
                "order_unpaid_amount": parent_unpaid,
                "expected_unpaid_amount": expected_unpaid,
                "parent_cost_amount": parent_cost,
                "project_cost_total": cost_total,
                "project_cost_count": cost_count,
                "order_gross_profit": parent_profit,
                "expected_gross_profit": expected_profit,
            },
            "associations": {
                "tasks": task_summary,
                "acceptance": {
                    "forms": len(forms),
                    "accepted_forms": sum(form.status == "accepted" for form in forms),
                    "items": len(acceptance_rows),
                    "mapped_active_item_refs": sum(
                        row.document_item_id in active_item_ids
                        for row, _ in acceptance_rows
                        if row.document_item_id
                    ),
                },
                "outsource": {
                    "active_tasks": len(outsource_rows),
                    "completed_or_settled": sum(
                        row.status in {"completed", "settled"} for row in outsource_rows
                    ),
                    "planned_total_amount": sum(
                        (self._to_decimal(row.total_amount) for row in outsource_rows),
                        Decimal("0"),
                    ),
                    "item_mapping": "stable_order_item_id_when_present",
                },
                "stock": {
                    "records": len(stock_rows),
                    "in_quantity": sum(
                        (self._to_decimal(row.quantity) for row in stock_rows if row.record_type == "in"),
                        Decimal("0"),
                    ),
                    "out_quantity": sum(
                        (self._to_decimal(row.quantity) for row in stock_rows if row.record_type == "out"),
                        Decimal("0"),
                    ),
                },
                "contracts": {
                    "direct_contracts": len(contract_rows),
                    "statuses": {
                        status: sum(contract.status == status for contract in contract_rows)
                        for status in sorted({contract.status for contract in contract_rows})
                    },
                },
                "framework_contract_projects": len(framework_rows),
                "vehicles": vehicle_summary,
                "confirmed_statements": confirmed_statement_count,
                "cdr": cdr_summary,
            },
            "orphan_references": orphan_references,
            "history": history_check,
            "change_batch": batch,
        })

    async def _build_order_item_mutation_context(
        self,
        doc,
        operation: str,
        item_id: UUID | None,
        data: dict | None,
    ) -> dict:
        if operation not in {"add", "update", "delete"}:
            raise ValueError("不支持的订单明细操作")
        if operation in {"update", "delete"} and not item_id:
            raise ValueError("修改或删除明细必须提供明细 ID")

        items = await self.repo.get_items(doc.id)
        current_item = None
        if item_id:
            current_item = await self.repo.get_item(item_id, document_id=doc.id)
            if not current_item:
                raise ValueError("订单明细不存在或不属于当前订单")

        input_data = {
            key: value
            for key, value in (data or {}).items()
            if key in ORDER_ITEM_FIELDS
        }
        normalized = None
        if operation == "add":
            if not str(input_data.get("item_name") or "").strip():
                raise ValueError("订单明细名称不能为空")
            normalized = normalize_quote_item_data(input_data)
            normalized["item_name"] = str(normalized["item_name"]).strip()
        elif operation == "update":
            if not input_data:
                raise ValueError("没有可更新的订单明细字段")
            merged = self._to_order_item_input(current_item)
            merged.update(input_data)
            normalized = normalize_quote_item_data(merged)
            if not str(normalized.get("item_name") or "").strip():
                raise ValueError("订单明细名称不能为空")
            normalized["item_name"] = str(normalized["item_name"]).strip()

        projected_items = []
        for item in items:
            projected = self._to_order_item_input(item)
            projected.update({
                "id": item.id,
                "source_quote_item_id": item.source_quote_item_id,
                "area": item.area,
                "subtotal_amount": item.subtotal_amount,
            })
            if operation == "update" and item.id == item_id:
                projected.update(normalized or {})
            projected_items.append(projected)
        if operation == "add":
            projected_items.append({**(normalized or {}), "id": None, "source_quote_item_id": None})
        elif operation == "delete":
            projected_items = [item for item in projected_items if item["id"] != item_id]

        relations = await self._collect_order_item_relations(doc, item_id=item_id)

        before_total = sum(
            (self._to_decimal(item.subtotal_amount) for item in items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        after_total = sum(
            (self._to_decimal(item.get("subtotal_amount")) for item in projected_items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        paid_amount = await self._get_nonvoided_payment_total(doc.id)
        cost_amount = self._to_decimal(getattr(doc, "cost_amount", 0)).quantize(MONEY_QUANTUM)
        after_unpaid = (after_total - paid_amount).quantize(MONEY_QUANTUM)
        decision = self._order_item_mutation_decision(
            doc,
            relations,
            operation=operation,
            after_total=after_total,
            paid_amount=paid_amount,
        )
        if operation == "delete" and len(items) <= 1:
            decision["lock_reasons"].append({
                "code": "LAST_ITEM",
                "message": "订单至少需要保留一条明细",
            })
            decision["can_apply"] = False
            decision["decision"] = "BLOCK"

        before_unpaid = (before_total - paid_amount).quantize(MONEY_QUANTUM)
        before_financials = {
            "total_amount": before_total,
            "paid_amount": paid_amount,
            "unpaid_amount": before_unpaid,
            "cost_amount": cost_amount,
            "gross_profit": (before_total - cost_amount).quantize(MONEY_QUANTUM),
            "line_count": len(items),
        }
        after_financials = {
            "total_amount": after_total,
            "paid_amount": paid_amount,
            "unpaid_amount": after_unpaid,
            "cost_amount": cost_amount,
            "gross_profit": (after_total - cost_amount).quantize(MONEY_QUANTUM),
            "line_count": len(projected_items),
        }
        projected_item = None
        if operation == "add":
            projected_item = projected_items[-1]
        elif current_item:
            projected_item = next(
                (item for item in projected_items if item["id"] == current_item.id),
                self._item_snapshot(current_item),
            )
        if projected_item:
            projected_item["specification"] = _build_spec(projected_item)

        return {
            "operation": operation,
            "item_id": str(item_id) if item_id else None,
            "before": self._json_safe(before_financials),
            "after": self._json_safe(after_financials),
            "delta": float(after_total - before_total),
            "projected_item": self._json_safe(projected_item),
            "decision": decision["decision"],
            "associated_edit_enabled": settings.ORDER_ITEM_ASSOCIATED_EDIT_ENABLED,
            "requires_confirmation": decision["requires_confirmation"],
            "requires_high_risk_ack": decision["requires_high_risk_ack"],
            "association_count": decision["association_count"],
            "lock_reasons": decision["lock_reasons"],
            "can_apply": decision["can_apply"],
            "association_catalog": self._json_safe(relations.get("association_catalog") or []),
            "refresh_plan": self._json_safe(relations.get("association_catalog") or []),
            "relations": self._json_safe(relations),
            "normalized": normalized,
        }

    async def preview_order_item_mutation(
        self,
        doc_id: UUID,
        operation: str,
        *,
        item_id: UUID | None = None,
        data: dict | None = None,
        expected_updated_at: str | None = None,
        reason: str | None = None,
        operated_by: UUID | None = None,
    ) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "order":
            raise ValueError("订单不存在")
        self._assert_expected_updated_at(doc, expected_updated_at)
        context = await self._build_order_item_mutation_context(doc, operation, item_id, data)
        preview_id = str(uuid4())
        preview_expires_at = (datetime.now() + MUTATION_PREVIEW_TTL).isoformat()
        preview_reason = (reason or "订单明细变更预览").strip()
        plan_hash = self._make_preview_hash(
            doc_id=doc.id,
            operation=operation,
            item_id=item_id,
            data=data,
            reason=preview_reason,
            expected_updated_at=expected_updated_at,
            preview_id=preview_id,
            preview_expires_at=preview_expires_at,
            context=context,
            operated_by=operated_by,
        )
        context.pop("normalized", None)
        return {
            "order_id": str(doc.id),
            "order_no": doc.doc_no,
            "status": doc.status,
            "updated_at": self._version_value(doc),
            "preview_id": preview_id,
            "preview_expires_at": preview_expires_at,
            "plan_hash": plan_hash,
            "change_status": "PREVIEWED",
            "verification_status": "PENDING",
            **context,
        }

    async def _recalculate_order_financials(self, doc) -> None:
        items = await self.repo.get_items(doc.id)
        total = sum(
            (self._to_decimal(item.subtotal_amount) for item in items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        paid = await self._get_nonvoided_payment_total(doc.id)
        if total < paid:
            raise ValueError("变更后订单总额不能低于已收款金额")
        cost = self._to_decimal(getattr(doc, "cost_amount", 0)).quantize(MONEY_QUANTUM)
        doc.total_amount = total
        doc.paid_amount = paid.quantize(MONEY_QUANTUM)
        doc.unpaid_amount = (total - paid).quantize(MONEY_QUANTUM)
        doc.cost_amount = cost
        doc.gross_profit = (total - cost).quantize(MONEY_QUANTUM)
        # 明细是独立子表，不能依赖父表 onupdate 自动触发版本变化。
        # 每次明细提交都显式推进订单版本，避免相同总额的变更绕过乐观锁。
        doc.updated_at = datetime.now()
        await self.db.flush()

    async def _apply_order_item_refresh(
        self,
        doc,
        *,
        operation: str,
        item_id: UUID | None,
        projected_item: dict | None,
        relation_catalog: list[dict],
        change_batch_id: str,
    ) -> dict:
        """Apply only stable, reversible downstream refreshes.

        Order-level records without an item FK are deliberately recorded as
        review work. This keeps the impact visible without guessing which line
        a task, stock movement, payment, or contract represents.
        """
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.models.outsource import OutsourceTask

        result = {
            "status": "VERIFIED",
            "change_batch_id": change_batch_id,
            "auto_refreshed": [],
            "preserved_facts": [],
            "pending_review": [],
            "adjustments": [],
            "blocked": [],
        }

        def append(bucket: str, entry: dict, detail: str) -> None:
            result[bucket].append({
                "module": entry.get("module"),
                "label": entry.get("label"),
                "record_id": entry.get("record_id"),
                "record_no": entry.get("record_no"),
                "status": entry.get("status"),
                "action": entry.get("action"),
                "detail": detail,
            })

        acceptance_item_ids = [
            UUID(entry["record_id"])
            for entry in relation_catalog
            if entry.get("module") == "acceptance_items" and entry.get("record_id")
        ]
        if acceptance_item_ids:
            acceptance_result = await self.db.execute(
                select(AcceptanceItem, AcceptanceForm)
                .join(AcceptanceForm, AcceptanceForm.id == AcceptanceItem.acceptance_id)
                .where(AcceptanceItem.id.in_(acceptance_item_ids))
            )
            for acceptance_item, form in acceptance_result.all():
                if form.status in {"draft", "pending", "rejected"} and acceptance_item.item_status not in {"accepted", "conditional"}:
                    if operation == "delete":
                        acceptance_item.document_item_id = None
                        append(
                            "auto_refreshed",
                            {
                                "module": "acceptance_items",
                                "label": "验收明细",
                                "record_id": str(acceptance_item.id),
                                "record_no": form.acceptance_no,
                                "status": acceptance_item.item_status,
                                "action": "refresh_draft",
                            },
                            "订单明细作废，未提交验收行解除明细引用并保留记录",
                        )
                    elif operation == "update" and projected_item:
                        acceptance_item.item_name = projected_item.get("item_name") or acceptance_item.item_name
                        acceptance_item.material_process = projected_item.get("material_process")
                        acceptance_item.specification = projected_item.get("specification")
                        acceptance_item.quantity = projected_item.get("quantity")
                        acceptance_item.unit = projected_item.get("unit")
                        acceptance_item.area = projected_item.get("area")
                        acceptance_item.unit_price = projected_item.get("unit_price")
                        acceptance_item.subtotal = projected_item.get("subtotal_amount")
                        acceptance_item.image_url = projected_item.get("image_url")
                        acceptance_item.group_name = projected_item.get("group_name")
                        append(
                            "auto_refreshed",
                            {
                                "module": "acceptance_items",
                                "label": "验收明细",
                                "record_id": str(acceptance_item.id),
                                "record_no": form.acceptance_no,
                                "status": acceptance_item.item_status,
                                "action": "refresh_draft",
                            },
                            "草稿验收明细已按订单明细刷新",
                        )
                else:
                    append(
                        "preserved_facts",
                        {
                            "module": "acceptance_items",
                            "label": "验收明细",
                            "record_id": str(acceptance_item.id),
                            "record_no": form.acceptance_no,
                            "status": acceptance_item.item_status,
                            "action": "preserve_fact_and_adjust",
                        },
                        "已验收事实保留，订单变更差异待调整",
                    )

        outsource_ids = [
            UUID(entry["record_id"])
            for entry in relation_catalog
            if entry.get("module") == "outsource_tasks" and entry.get("record_id")
        ]
        if outsource_ids:
            outsource_result = await self.db.execute(
                select(OutsourceTask).where(OutsourceTask.id.in_(outsource_ids))
            )
            for task in outsource_result.scalars().all():
                if task.status in {"pending", "draft"} and task.order_item_id == item_id:
                    paid_amount = self._to_decimal(task.paid_amount)
                    if operation == "delete":
                        if paid_amount > 0:
                            append(
                                "adjustments",
                                {
                                    "module": "outsource_tasks",
                                    "label": "外协任务",
                                    "record_id": str(task.id),
                                    "record_no": task.task_no,
                                    "status": task.status,
                                    "action": "preserve_fact_and_adjust",
                                },
                                "外协任务已有付款，不能自动作废，需人工处理退款或冲销",
                            )
                        else:
                            task.status = "cancelled"
                            task.deleted_at = datetime.now()
                            append(
                                "auto_refreshed",
                                {
                                    "module": "outsource_tasks",
                                    "label": "外协任务",
                                    "record_id": str(task.id),
                                    "record_no": task.task_no,
                                    "status": task.status,
                                    "action": "refresh_plan",
                                },
                                "未开始外协任务已作废，原记录保留用于追溯",
                            )
                    elif operation == "update" and projected_item:
                        quantity = self._to_decimal(projected_item.get("quantity"))
                        # 订单明细的 unit_price/subtotal_amount 是销售价，外协任务的
                        # unit_price/total_amount 是供应商成本。订单变更只刷新描述、
                        # 数量和按原外协成本单价重算的计划金额，绝不复制销售价。
                        vendor_unit_price = self._to_decimal(task.unit_price).quantize(MONEY_QUANTUM)
                        projected_total = (quantity * vendor_unit_price).quantize(
                            MONEY_QUANTUM
                        )
                        if paid_amount > projected_total:
                            append(
                                "adjustments",
                                {
                                    "module": "outsource_tasks",
                                    "label": "外协任务",
                                    "record_id": str(task.id),
                                    "record_no": task.task_no,
                                    "status": task.status,
                                    "action": "preserve_fact_and_adjust",
                                },
                                "变更后外协计划金额低于已付款金额，需人工处理差额",
                            )
                        else:
                            task.description = projected_item.get("item_name") or task.description
                            task.quantity = quantity
                            task.total_amount = projected_total
                            task.unpaid_amount = max(
                                task.total_amount - self._to_decimal(task.paid_amount),
                                Decimal("0"),
                            )
                            append(
                                "auto_refreshed",
                                {
                                    "module": "outsource_tasks",
                                    "label": "外协任务",
                                    "record_id": str(task.id),
                                    "record_no": task.task_no,
                                    "status": task.status,
                                    "action": "refresh_plan",
                                },
                                "未开始外协任务已按订单明细刷新数量，成本单价沿用原外协任务",
                            )
                    else:
                        append(
                            "pending_review",
                            {
                                "module": "outsource_tasks",
                                "label": "外协任务",
                                "record_id": str(task.id),
                                "record_no": task.task_no,
                                "status": task.status,
                                "action": "refresh_plan",
                            },
                            "该外协任务只有订单级关联，无法安全映射到本次变更，需人工复核",
                        )
                elif task.status in {"completed", "settled"}:
                    append(
                        "preserved_facts",
                        {
                            "module": "outsource_tasks",
                            "label": "外协任务",
                            "record_id": str(task.id),
                            "record_no": task.task_no,
                            "status": task.status,
                            "action": "preserve_fact_and_adjust",
                        },
                        "已执行/已结算外协事实保留，差异待调整",
                    )
                elif task.status in {"pending", "draft"}:
                    append(
                        "pending_review",
                        {
                            "module": "outsource_tasks",
                            "label": "外协任务",
                            "record_id": str(task.id),
                            "record_no": task.task_no,
                            "status": task.status,
                            "action": "refresh_plan",
                        },
                        "该外协任务只有订单级关联，无法安全映射到本次明细，需人工复核",
                    )

        for entry in relation_catalog:
            module = entry.get("module")
            if module in {"acceptance_items", "outsource_tasks"}:
                continue
            action = entry.get("action")
            if action in {"preserve_fact_and_reconcile", "preserve_fact_and_adjust"}:
                append("preserved_facts", entry, entry.get("note") or "历史事实保留")
                if action == "preserve_fact_and_adjust":
                    append("adjustments", entry, entry.get("note") or "请处理差异调整")
            elif action in {"preserve_fact_and_review", "refresh_plan_or_review", "review_required"}:
                append("pending_review", entry, entry.get("note") or "请人工复核")
            elif action == "refresh_draft":
                append("pending_review", entry, "关联单据可刷新，但明细映射需复核")
            else:
                append("pending_review", entry, entry.get("note") or "请人工复核")

        if result["blocked"]:
            result["status"] = "BLOCKED"
        elif result["pending_review"] or result["adjustments"]:
            result["status"] = "PENDING_ADJUSTMENT"
        result["counts"] = {
            key: len(result[key])
            for key in (
                "auto_refreshed",
                "preserved_facts",
                "pending_review",
                "adjustments",
                "blocked",
            )
        }
        await self.db.flush()
        return self._json_safe(result)

    @staticmethod
    def _stable_order_edit_value(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return value

    @classmethod
    def _order_edit_values_equal(cls, left, right) -> bool:
        return cls._stable_order_edit_value(left) == cls._stable_order_edit_value(right)

    @staticmethod
    def _merge_order_relation_contexts(contexts: list[dict]) -> dict:
        """Merge per-line and document-level relations without duplicate rows."""
        merged: dict = {
            "payments": 0,
            "acceptance_forms": 0,
            "accepted_acceptance_forms": 0,
            "acceptance_item_refs": 0,
            "source_item_refs": 0,
            "outsource_tasks": 0,
            "outsource_item_refs": 0,
            "project_costs": 0,
            "item_project_costs": 0,
            "stock_out_records": 0,
            "contract_links": 0,
            "framework_contract_links": 0,
            "vehicle_records": 0,
            "confirmed_statements": 0,
            "source_quote_refs": 0,
            "cdr_records": 0,
            "tasks": {"design": 0, "production": 0, "installation": 0, "total": 0},
        }
        catalog: dict[tuple[str, str], dict] = {}
        for context in contexts:
            if not context:
                continue
            for key in (
                "payments",
                "acceptance_forms",
                "accepted_acceptance_forms",
                "acceptance_item_refs",
                "source_item_refs",
                "outsource_tasks",
                "outsource_item_refs",
                "project_costs",
                "item_project_costs",
                "stock_out_records",
                "contract_links",
                "framework_contract_links",
                "vehicle_records",
                "confirmed_statements",
                "source_quote_refs",
                "cdr_records",
            ):
                merged[key] = max(int(merged.get(key) or 0), int(context.get(key) or 0))
            task_context = context.get("tasks") or {}
            for key in ("design", "production", "installation", "total"):
                merged["tasks"][key] = max(
                    int(merged["tasks"].get(key) or 0),
                    int(task_context.get(key) or 0),
                )
            for entry in context.get("association_catalog") or []:
                if not isinstance(entry, dict):
                    continue
                key = (str(entry.get("module") or ""), str(entry.get("record_id") or ""))
                catalog[key] = entry
        merged["association_catalog"] = sorted(
            catalog.values(),
            key=lambda entry: (
                str(entry.get("module") or ""),
                str(entry.get("record_id") or ""),
                str(entry.get("record_no") or ""),
            ),
        )
        return merged

    @classmethod
    def _order_edit_preview_hash(
        cls,
        *,
        doc_id: UUID,
        header: dict,
        items: list[dict],
        groups: list[dict],
        reason: str,
        expected_updated_at: str | None,
        preview_id: str,
        preview_expires_at: str,
        context: dict,
        operated_by: UUID | None,
    ) -> str:
        payload = {
            "order_id": str(doc_id),
            "header": cls._json_safe(header),
            "items": cls._json_safe(items),
            "groups": cls._json_safe(groups),
            "reason": reason.strip(),
            "expected_updated_at": expected_updated_at,
            "preview_id": preview_id,
            "preview_expires_at": preview_expires_at,
            "operated_by": str(operated_by) if operated_by else None,
            "context": cls._json_safe(context),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(_PREVIEW_SIGNING_SECRET, encoded, hashlib.sha256).hexdigest()

    async def _build_order_edit_context(
        self,
        doc,
        *,
        header: dict | None,
        items_data: list[dict],
        groups_data: list[dict],
    ) -> dict:
        """Build the full-document diff used by both preview and apply.

        Existing item IDs are updated in place. Missing IDs become lifecycle
        voids; they are never physically deleted or replaced with new IDs.
        """
        if doc.doc_type != "order":
            raise ValueError("当前单据不是订单")

        header = dict(header or {})
        unknown_header_fields = set(header) - set(ORDER_EDIT_HEADER_FIELDS)
        if unknown_header_fields:
            raise ValueError("订单头包含不可编辑字段")

        normalized_header: dict = {}
        header_diff: list[dict] = []
        for field in ORDER_EDIT_HEADER_FIELDS:
            if field not in header:
                continue
            value = header[field]
            if field == "delivery_deadline" and isinstance(value, str):
                value = (
                    datetime.combine(date.fromisoformat(value), datetime.min.time())
                    if value
                    else None
                )
            if isinstance(value, str):
                value = value.strip()
            if field == "project_name" and not value:
                raise ValueError("项目名称不能为空")
            normalized_header[field] = value

            if field == "customer_id":
                before_value = str(doc.customer_id) if doc.customer_id else None
                after_value = str(value) if value else None
            elif field == "customer_name":
                before_value = doc.customer_name
                after_value = value
            elif field == "delivery_deadline":
                before_value = (
                    doc.delivery_deadline.date()
                    if isinstance(doc.delivery_deadline, datetime)
                    else doc.delivery_deadline
                )
                after_value = value.date() if isinstance(value, datetime) else value
            else:
                before_value = getattr(doc, field, None)
                after_value = value
            if not self._order_edit_values_equal(before_value, after_value):
                header_diff.append({
                    "field": field,
                    "before": self._stable_order_edit_value(before_value),
                    "after": self._stable_order_edit_value(after_value),
                })

        current_items = await self.repo.get_items(doc.id)
        current_by_id = {item.id: item for item in current_items}
        seen_ids: set[UUID] = set()
        normalized_items: list[dict] = []
        operations: list[dict] = []

        for index, raw_item in enumerate(items_data):
            raw = dict(raw_item)
            raw_id = raw.pop("id", None)
            item_id = None
            if raw_id:
                try:
                    item_id = UUID(str(raw_id))
                except (TypeError, ValueError) as exc:
                    raise ValueError("订单明细 ID 格式无效") from exc
                if item_id in seen_ids:
                    raise ValueError("订单编辑中存在重复的明细 ID")
                seen_ids.add(item_id)
                current_item = current_by_id.get(item_id)
                if not current_item:
                    raise ValueError("订单明细不存在或不属于当前订单")
                merged = self._to_order_item_input(current_item)
                merged.update(raw)
                normalized = normalize_quote_item_data(merged)
            else:
                normalized = normalize_quote_item_data(raw)

            item_name = str(normalized.get("item_name") or "").strip()
            if not item_name:
                raise ValueError("订单明细名称不能为空")
            normalized["item_name"] = item_name
            normalized["sort_order"] = index
            normalized["group_name"] = normalized.get("group_name") or None
            normalized["group_id"] = normalized.get("group_id") or None
            normalized_items.append(normalized)
            projected_item = dict(normalized)
            projected_item["specification"] = _build_spec(projected_item)

            if item_id is None:
                operations.append({
                    "operation": "add",
                    "item_id": None,
                    "item": projected_item,
                    "changed_fields": list(ORDER_ITEM_FIELDS),
                })
                continue

            current_item = current_by_id[item_id]
            changed_fields = [
                field
                for field in ORDER_ITEM_FIELDS
                if not self._order_edit_values_equal(
                    getattr(current_item, field, None),
                    normalized.get(field),
                )
            ]
            if changed_fields:
                operations.append({
                    "operation": "update",
                    "item_id": item_id,
                    "item": projected_item,
                    "changed_fields": changed_fields,
                })

        for current_item in current_items:
            if current_item.id not in seen_ids:
                operations.append({
                    "operation": "delete",
                    "item_id": current_item.id,
                    "item": self._item_snapshot(current_item),
                    "changed_fields": ["lifecycle_status"],
                })

        existing_groups = await self.repo.get_groups(doc.id)
        normalized_groups = [
            {
                "group_id": str(group.get("group_id") or "").strip(),
                "group_name": (str(group.get("group_name")).strip() if group.get("group_name") else None),
                "sort_order": index,
            }
            for index, group in enumerate(groups_data or [])
        ]
        if any(not group["group_id"] for group in normalized_groups):
            raise ValueError("订单分组 ID 不能为空")
        current_groups = [
            {
                "group_id": str(group.group_id),
                "group_name": group.group_name,
                "sort_order": group.sort_order,
            }
            for group in sorted(
                existing_groups,
                key=lambda group: (group.sort_order or 0, group.created_at),
            )
        ]
        groups_changed = current_groups != normalized_groups

        relation_contexts: list[dict] = []
        for operation in operations:
            if operation["operation"] in {"update", "delete"}:
                relation_context = await self._collect_order_item_relations(
                    doc,
                    item_id=operation["item_id"],
                )
                operation["_relation_context"] = relation_context
                relation_contexts.append(relation_context)
        if any(operation["operation"] == "add" for operation in operations) or header_diff or groups_changed:
            relation_contexts.append(
                await self._collect_order_item_relations(doc)
            )
        relations = self._merge_order_relation_contexts(relation_contexts)

        before_total = sum(
            (self._to_decimal(item.subtotal_amount) for item in current_items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        after_total = sum(
            (self._to_decimal(item.get("subtotal_amount")) for item in normalized_items),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        paid_amount = await self._get_nonvoided_payment_total(doc.id)
        cost_amount = self._to_decimal(getattr(doc, "cost_amount", 0)).quantize(MONEY_QUANTUM)
        decision = self._order_item_mutation_decision(
            doc,
            relations,
            operation="batch",
            after_total=after_total,
            paid_amount=paid_amount,
        )
        if not normalized_items:
            decision["lock_reasons"].append({
                "code": "LAST_ITEM",
                "message": "订单至少需要保留一条明细",
            })
            decision["can_apply"] = False
            decision["decision"] = "BLOCK"

        before_unpaid = (before_total - paid_amount).quantize(MONEY_QUANTUM)
        after_unpaid = (after_total - paid_amount).quantize(MONEY_QUANTUM)
        item_diffs = []
        for operation in operations:
            projected = operation.get("item") or {}
            item_diffs.append({
                "operation": operation["operation"],
                "item_id": str(operation["item_id"]) if operation.get("item_id") else None,
                "item_name": projected.get("item_name"),
                "changed_fields": operation.get("changed_fields") or [],
                "before": self._json_safe(
                    self._item_snapshot(current_by_id[operation["item_id"]])
                    if operation["operation"] in {"update", "delete"}
                    else None
                ),
                "after": self._json_safe(projected if operation["operation"] != "delete" else None),
            })

        return {
            "operation": "batch",
            "header": normalized_header,
            "header_diff": self._json_safe(header_diff),
            "items": normalized_items,
            "groups": normalized_groups,
            "groups_changed": groups_changed,
            "operations": operations,
            "item_diffs": item_diffs,
            "diff": {
                "added": sum(operation["operation"] == "add" for operation in operations),
                "updated": sum(operation["operation"] == "update" for operation in operations),
                "deleted": sum(operation["operation"] == "delete" for operation in operations),
                "header_changed": len(header_diff),
                "groups_changed": groups_changed,
            },
            "before": {
                "total_amount": before_total,
                "paid_amount": paid_amount,
                "unpaid_amount": before_unpaid,
                "cost_amount": cost_amount,
                "gross_profit": (before_total - cost_amount).quantize(MONEY_QUANTUM),
                "line_count": len(current_items),
            },
            "after": {
                "total_amount": after_total,
                "paid_amount": paid_amount,
                "unpaid_amount": after_unpaid,
                "cost_amount": cost_amount,
                "gross_profit": (after_total - cost_amount).quantize(MONEY_QUANTUM),
                "line_count": len(normalized_items),
            },
            "delta": after_total - before_total,
            "decision": decision["decision"],
            "associated_edit_enabled": settings.ORDER_ITEM_ASSOCIATED_EDIT_ENABLED,
            "requires_confirmation": decision["requires_confirmation"],
            "requires_high_risk_ack": decision["requires_high_risk_ack"],
            "association_count": decision["association_count"],
            "lock_reasons": decision["lock_reasons"],
            "can_apply": decision["can_apply"],
            "association_catalog": relations.get("association_catalog") or [],
            "refresh_plan": relations.get("association_catalog") or [],
            "relations": relations,
        }

    async def preview_order_edit(
        self,
        doc_id: UUID,
        *,
        header: dict | None,
        items: list[dict],
        groups: list[dict],
        expected_updated_at: str | None,
        reason: str | None,
        operated_by: UUID | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError("请填写订单变更原因")
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doc_type != "order":
            raise ValueError("订单不存在")
        self._assert_expected_updated_at(doc, expected_updated_at)
        context = await self._build_order_edit_context(
            doc,
            header=header,
            items_data=items,
            groups_data=groups,
        )
        preview_id = str(uuid4())
        preview_expires_at = (datetime.now() + MUTATION_PREVIEW_TTL).isoformat()
        plan_hash = self._order_edit_preview_hash(
            doc_id=doc.id,
            header=context["header"],
            items=context["items"],
            groups=context["groups"],
            reason=reason,
            expected_updated_at=expected_updated_at,
            preview_id=preview_id,
            preview_expires_at=preview_expires_at,
            context=context,
            operated_by=operated_by,
        )
        public_context = {
            key: value
            for key, value in context.items()
            if key not in {"header", "items", "groups", "operations"}
        }
        return {
            "order_id": str(doc.id),
            "order_no": doc.doc_no,
            "status": doc.status,
            "updated_at": self._version_value(doc),
            "preview_id": preview_id,
            "preview_expires_at": preview_expires_at,
            "plan_hash": plan_hash,
            "change_status": "PREVIEWED",
            "verification_status": "PENDING",
            **self._json_safe(public_context),
        }

    async def _apply_order_edit_header(self, doc, header: dict) -> None:
        customer_id = header.get("customer_id")
        customer_name = (header.get("customer_name") or "").strip()
        if customer_id:
            try:
                doc.customer_id = UUID(str(customer_id))
            except (TypeError, ValueError) as exc:
                raise ValueError("客户 ID 格式无效") from exc
            doc.customer_name = None
        elif "customer_name" in header and customer_name:
            doc.customer_id = None
            doc.customer_name = customer_name

        for field in ORDER_EDIT_HEADER_FIELDS:
            if field in {"customer_id", "customer_name"} or field not in header:
                continue
            setattr(doc, field, header[field])
        doc.updated_at = datetime.now()
        await self.db.flush()

    async def _sync_order_edit_groups(self, doc_id: UUID, groups: list[dict]) -> None:
        from app.models.business_document import BusinessDocumentGroup

        existing = await self.repo.get_groups(doc_id)
        existing_by_key = {str(group.group_id): group for group in existing}
        desired_keys = set()
        for index, group_data in enumerate(groups):
            key = str(group_data["group_id"])
            desired_keys.add(key)
            group = existing_by_key.get(key)
            if group is None:
                self.db.add(BusinessDocumentGroup(
                    document_id=doc_id,
                    group_id=key,
                    group_name=group_data.get("group_name"),
                    sort_order=index,
                ))
            else:
                group.group_name = group_data.get("group_name")
                group.sort_order = index
        for group in existing:
            if str(group.group_id) not in desired_keys:
                await self.db.delete(group)
        await self.db.flush()

    @staticmethod
    def _merge_order_edit_refresh_results(results: list[dict], change_batch_id: str) -> dict:
        merged = {
            "status": "VERIFIED",
            "change_batch_id": change_batch_id,
            "auto_refreshed": [],
            "preserved_facts": [],
            "pending_review": [],
            "adjustments": [],
            "blocked": [],
        }
        for result in results:
            if result.get("status") == "BLOCKED":
                merged["status"] = "BLOCKED"
            elif result.get("status") == "PENDING_ADJUSTMENT" and merged["status"] != "BLOCKED":
                merged["status"] = "PENDING_ADJUSTMENT"
            for bucket in (
                "auto_refreshed",
                "preserved_facts",
                "pending_review",
                "adjustments",
                "blocked",
            ):
                merged[bucket].extend(result.get(bucket) or [])
        merged["counts"] = {
            bucket: len(merged[bucket])
            for bucket in (
                "auto_refreshed",
                "preserved_facts",
                "pending_review",
                "adjustments",
                "blocked",
            )
        }
        return merged

    async def apply_order_edit(
        self,
        doc_id: UUID,
        *,
        header: dict | None,
        items: list[dict],
        groups: list[dict],
        expected_updated_at: str | None,
        reason: str | None,
        operated_by: UUID | None = None,
        operated_by_name: str | None = None,
        ip_address: str | None = None,
        preview_id: str | None = None,
        plan_hash: str | None = None,
        preview_expires_at: str | None = None,
        confirm_high_risk: bool = False,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError("请填写订单变更原因")
        doc = await self._get_locked_order(doc_id)
        if not doc:
            raise ValueError("订单不存在")
        already_applied = await self._find_applied_mutation(doc.id, preview_id)
        if already_applied:
            updated = await self.repo.get_by_id(doc.id)
            response = self._to_detail(updated)
            response["change_batch"] = {
                "change_batch_id": preview_id,
                "status": already_applied.get("change_status", "VERIFIED"),
                "idempotent_replay": True,
                "refresh_result": already_applied.get("refresh_result"),
            }
            return response

        self._assert_expected_updated_at(doc, expected_updated_at)
        context = await self._build_order_edit_context(
            doc,
            header=header,
            items_data=items,
            groups_data=groups,
        )
        if not context["can_apply"]:
            messages = "；".join(item["message"] for item in context["lock_reasons"])
            raise ValueError(f"订单编辑暂不可提交：{messages}")
        if context["requires_confirmation"] or preview_id or plan_hash or preview_expires_at:
            if not preview_id or not plan_hash or not preview_expires_at:
                raise ValueError("请先完成订单影响预检并确认关联刷新")
            try:
                expires_at = datetime.fromisoformat(preview_expires_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("订单影响预检凭证格式无效，请重新预检") from exc
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.now()
            if expires_at <= now:
                raise ValueError("订单影响预检已过期，请重新预检")
            expected_hash = self._order_edit_preview_hash(
                doc_id=doc.id,
                header=context["header"],
                items=context["items"],
                groups=context["groups"],
                reason=reason,
                expected_updated_at=expected_updated_at,
                preview_id=preview_id,
                preview_expires_at=preview_expires_at,
                context=context,
                operated_by=operated_by,
            )
            if not hmac.compare_digest(expected_hash, plan_hash):
                raise ValueError("订单影响目录已变化，请重新预检后确认")
            if context["requires_high_risk_ack"] and not confirm_high_risk:
                raise ValueError("高风险关联变更需要明确确认后才能提交")

        before_snapshot = self._to_detail(doc)
        await self._apply_order_edit_header(doc, context["header"])
        active_items = {item.id: item for item in await self.repo.get_items(doc.id)}
        refresh_results = []
        change_batch_id = preview_id or str(uuid4())

        for operation in context["operations"]:
            operation_type = operation["operation"]
            if operation_type == "add":
                new_item_data = dict(operation["item"])
                new_item_data.pop("id", None)
                new_item_data.pop("specification", None)
                added = await self.repo.add_items(doc.id, [new_item_data])
                if added:
                    operation["item_id"] = added[0].id
            elif operation_type == "update":
                item = active_items.get(operation["item_id"])
                if not item:
                    raise ValueError("订单明细不存在或已被其他操作作废")
                for field in ORDER_ITEM_FIELDS:
                    setattr(item, field, operation["item"].get(field))
                item.area = operation["item"].get("area")
                item.subtotal_amount = operation["item"].get("subtotal_amount")
                await self.db.flush()
            elif operation_type == "delete":
                item = active_items.get(operation["item_id"])
                if not item:
                    raise ValueError("订单明细不存在或已被其他操作作废")
                item.lifecycle_status = "voided"
                item.voided_at = datetime.now()
                item.void_reason = reason.strip()
                await self.db.flush()

            if operation_type in {"update", "delete"}:
                refresh_results.append(
                    await self._apply_order_item_refresh(
                        doc,
                        operation=operation_type,
                        item_id=operation["item_id"],
                        projected_item=(
                            operation.get("item")
                            if operation_type == "update"
                            else None
                        ),
                        relation_catalog=(operation.get("_relation_context") or {}).get("association_catalog") or [],
                        change_batch_id=change_batch_id,
                    )
                )

        # 新增明细、分组或订单头变更无法映射到某一条既有关联明细时，
        # 仍要把订单级关联纳入变更批次，避免界面列出了影响项但结果状态却误报为已核验。
        if (
            not refresh_results
            and context["association_catalog"]
            and (
                context["header_diff"]
                or context["groups_changed"]
                or any(operation["operation"] == "add" for operation in context["operations"])
            )
        ):
            refresh_results.append(
                await self._apply_order_item_refresh(
                    doc,
                    operation="update",
                    item_id=None,
                    projected_item=None,
                    relation_catalog=context["association_catalog"],
                    change_batch_id=change_batch_id,
                )
            )

        if context["groups_changed"]:
            await self._sync_order_edit_groups(doc.id, context["groups"])
        if context["operations"]:
            await self._recalculate_order_financials(doc)
        else:
            doc.updated_at = datetime.now()
            await self.db.flush()

        await self._sync_contact_to_customer(doc, context["header"])
        if any(field in context["header"] for field in ("project_name", "department")):
            await self._sync_framework_contract_projects(doc)

        refresh_result = self._merge_order_edit_refresh_results(refresh_results, change_batch_id)
        updated = await self.repo.get_by_id(doc.id)
        await self.db.refresh(
            updated,
            [
                "customer",
                "items",
                "groups",
                "status_logs",
                "design_tasks",
                "production_tasks",
                "installation_tasks",
            ],
        )
        after_snapshot = self._to_detail(updated)
        final_change_status = refresh_result.get("status", "VERIFIED")
        audit_snapshot = {
            "change_batch_id": change_batch_id,
            "operator_id": str(operated_by) if operated_by else None,
            "change_status": final_change_status,
            "status_history": ["PREVIEWED", "VERIFYING", final_change_status],
            "verification_status": "VERIFIED" if final_change_status == "VERIFIED" else final_change_status,
            "change_type": "order_edit_batch",
            "reason": reason.strip(),
            "header_diff": context["header_diff"],
            "diff": context["diff"],
            "item_diffs": context["item_diffs"],
            "before": before_snapshot,
            "after": after_snapshot,
            "refresh_result": refresh_result,
            "impact": {
                "decision": context["decision"],
                "association_catalog": context["association_catalog"],
                "relations": context["relations"],
            },
        }
        version_no = await self.repo.get_next_version_no(doc.id)
        await self.repo.create_version(
            doc.id,
            version_no,
            self._json_safe(audit_snapshot),
            operated_by,
        )
        from app.services.operation_log_service import ACTION_UPDATE, OBJ_ORDER, log_operation

        await log_operation(
            self.db,
            operated_by,
            operated_by_name,
            OBJ_ORDER,
            doc.id,
            ACTION_UPDATE,
            ip_address=ip_address,
            before_data=self._json_safe(before_snapshot),
            after_data=self._json_safe(audit_snapshot),
        )
        await self.db.flush()
        after_snapshot["change_batch"] = {
            "change_batch_id": change_batch_id,
            "status": final_change_status,
            "status_history": ["PREVIEWED", "VERIFYING", final_change_status],
            "verification_status": "VERIFIED" if final_change_status == "VERIFIED" else final_change_status,
            "refresh_result": refresh_result,
            "idempotent_replay": False,
        }
        return after_snapshot

    async def mutate_order_item(
        self,
        doc_id: UUID,
        operation: str,
        *,
        item_id: UUID | None = None,
        data: dict | None = None,
        expected_updated_at: str | None = None,
        reason: str | None = None,
        operated_by: UUID | None = None,
        operated_by_name: str | None = None,
        ip_address: str | None = None,
        preview_id: str | None = None,
        plan_hash: str | None = None,
        preview_expires_at: str | None = None,
        confirm_high_risk: bool = False,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError("请填写订单明细变更原因")
        doc = await self._get_locked_order(doc_id)
        if not doc:
            raise ValueError("订单不存在")
        already_applied = await self._find_applied_mutation(doc.id, preview_id)
        if already_applied:
            updated = await self.repo.get_by_id(doc.id)
            response = self._to_detail(updated)
            response["change_batch"] = {
                "change_batch_id": preview_id,
                "status": already_applied.get("change_status", "VERIFIED"),
                "idempotent_replay": True,
                "refresh_result": already_applied.get("refresh_result"),
            }
            return response
        self._assert_expected_updated_at(doc, expected_updated_at)
        context = await self._build_order_item_mutation_context(doc, operation, item_id, data)
        if not context["can_apply"]:
            messages = "；".join(item["message"] for item in context["lock_reasons"])
            raise ValueError(f"订单明细暂不可修改：{messages}")
        if context["requires_confirmation"]:
            self._assert_preview_confirmation(
                preview_id=preview_id,
                plan_hash=plan_hash,
                preview_expires_at=preview_expires_at,
                doc_id=doc.id,
                operation=operation,
                item_id=item_id,
                data=data,
                reason=reason,
                expected_updated_at=expected_updated_at,
                operated_by=operated_by,
                context=context,
            )
            if context["requires_high_risk_ack"] and not confirm_high_risk:
                raise ValueError("高风险关联变更需要明确确认后才能提交")
        elif preview_id or plan_hash or preview_expires_at:
            self._assert_preview_confirmation(
                preview_id=preview_id,
                plan_hash=plan_hash,
                preview_expires_at=preview_expires_at,
                doc_id=doc.id,
                operation=operation,
                item_id=item_id,
                data=data,
                reason=reason,
                expected_updated_at=expected_updated_at,
                operated_by=operated_by,
                context=context,
            )

        before_snapshot = self._to_detail(doc)
        normalized = context["normalized"]
        if operation == "add":
            await self.repo.add_items(doc.id, [dict(normalized or {})])
        elif operation == "update":
            item = await self.repo.get_item(item_id, document_id=doc.id)
            if not item:
                raise ValueError("订单明细不存在或不属于当前订单")
            for field in ORDER_ITEM_FIELDS:
                if normalized and field in normalized:
                    setattr(item, field, normalized[field])
            item.area = normalized["area"]
            item.subtotal_amount = normalized["subtotal_amount"]
            await self.db.flush()
        elif operation == "delete":
            item = await self.repo.get_item(item_id, document_id=doc.id)
            if not item:
                raise ValueError("订单明细不存在或不属于当前订单")
            item.lifecycle_status = "voided"
            item.voided_at = datetime.now()
            item.void_reason = reason.strip()
            await self.db.flush()
        else:
            raise ValueError("不支持的订单明细操作")

        await self._recalculate_order_financials(doc)
        change_batch_id = preview_id or str(uuid4())
        refresh_result = await self._apply_order_item_refresh(
            doc,
            operation=operation,
            item_id=item_id,
            projected_item=context.get("projected_item"),
            relation_catalog=context.get("association_catalog") or [],
            change_batch_id=change_batch_id,
        )
        updated = await self.repo.get_by_id(doc.id)
        await self.db.refresh(
            updated,
            [
                "customer",
                "items",
                "groups",
                "status_logs",
                "design_tasks",
                "production_tasks",
                "installation_tasks",
            ],
        )
        after_snapshot = self._to_detail(updated)
        final_change_status = refresh_result.get("status", "VERIFIED")
        audit_snapshot = {
            "change_batch_id": change_batch_id,
            "operator_id": str(operated_by) if operated_by else None,
            "change_status": final_change_status,
            "status_history": ["PREVIEWED", "VERIFYING", final_change_status],
            "verification_status": (
                "VERIFIED"
                if final_change_status == "VERIFIED"
                else final_change_status
            ),
            "change_type": f"order_item_{operation}",
            "reason": reason.strip(),
            "before": before_snapshot,
            "after": after_snapshot,
            "refresh_result": refresh_result,
            "impact": {
                key: value
                for key, value in context.items()
                if key not in {"normalized"}
            },
        }
        version_no = await self.repo.get_next_version_no(doc.id)
        await self.repo.create_version(
            doc.id,
            version_no,
            self._json_safe(audit_snapshot),
            operated_by,
        )
        from app.services.operation_log_service import (
            ACTION_ITEM_ADD,
            ACTION_ITEM_DELETE,
            ACTION_ITEM_UPDATE,
            OBJ_ORDER,
            log_operation,
        )

        action = {
            "add": ACTION_ITEM_ADD,
            "update": ACTION_ITEM_UPDATE,
            "delete": ACTION_ITEM_DELETE,
        }[operation]
        await log_operation(
            self.db,
            operated_by,
            operated_by_name,
            OBJ_ORDER,
            doc.id,
            action,
            ip_address=ip_address,
            before_data=self._json_safe(before_snapshot),
            after_data=self._json_safe(audit_snapshot),
        )
        await self.db.flush()
        after_snapshot["change_batch"] = {
            "change_batch_id": change_batch_id,
            "status": final_change_status,
            "status_history": ["PREVIEWED", "VERIFYING", final_change_status],
            "verification_status": (
                "VERIFIED" if final_change_status == "VERIFIED" else final_change_status
            ),
            "refresh_result": refresh_result,
            "idempotent_replay": False,
        }
        return after_snapshot

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
                "quote_date": d.quote_date.isoformat() if d.quote_date else None,
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
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "groups": [
                {
                    "id": str(group.id),
                    "quote_id": str(d.id),
                    "group_id": group.group_id,
                    "group_name": group.group_name,
                    "sort_order": group.sort_order,
                }
                for group in sorted(
                    (d.groups or []),
                    key=lambda group: (group.sort_order or 0, group.created_at),
                )
            ],
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
                    "group_id": it.group_id,
                    "group_name": it.group_name,
                    "material_process": it.material_process,
                    "lifecycle_status": getattr(it, "lifecycle_status", "active"),
                }
                for it in (d.items or [])
                if getattr(it, "lifecycle_status", "active") == "active"
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
                "quote_date": d.quote_date.isoformat() if d.quote_date else None,
            })

        return base
