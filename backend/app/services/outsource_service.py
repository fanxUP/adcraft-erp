import re
from uuid import UUID
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.outsource_repo import OutsourceVendorRepository, OutsourceTaskRepository, OutsourcePaymentRepository
from app.services.number_generator import generate_vendor_no, generate_outsource_task_no, generate_outsource_payment_no
from app.models.outsource import OutsourceVendor, OutsourcePayment, OutsourceTask
from app.domain.workflows import OUTSOURCE_TASK_WORKFLOW, ensure_transition


MONEY_QUANTUM = Decimal("0.01")
ITEM_OUTSOURCE_TASK_TYPES = frozenset({"design", "production", "installation"})


class OutsourceService:
    SOURCE_TASK_LABELS = {
        "design": "设计",
        "production": "制作",
        "installation": "安装",
    }
    DOCUMENT_LABELS = {
        "order": "订单",
        "quote": "报价单",
    }
    GROUP_KEY_PATTERNS = (
        ("source_task", re.compile(
            r"^source:(design|production|installation):([0-9a-fA-F-]{36})$"
        )),
        ("related_document", re.compile(
            r"^document:(order|quote):([0-9a-fA-F-]{36})$"
        )),
        ("task", re.compile(r"^task:([0-9a-fA-F-]{36})$")),
    )

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_repo = OutsourceVendorRepository(db)
        self.task_repo = OutsourceTaskRepository(db)
        self.payment_repo = OutsourcePaymentRepository(db)

    @staticmethod
    def _to_decimal(value, default: str = "0") -> Decimal:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))

    @staticmethod
    def _to_money(value) -> Decimal:
        return OutsourceService._to_decimal(value).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _to_uuid(value: UUID | str | None) -> UUID | None:
        if value is None or value == "":
            return None
        return value if isinstance(value, UUID) else UUID(str(value))

    def _normalize_task_data(self, data: dict) -> dict:
        """Normalize compatibility aliases without losing explicit nulls."""
        normalized = dict(data)
        normalized.pop("related_project_name", None)

        if "order_id" in normalized:
            if not normalized.get("related_doc_id"):
                normalized["related_doc_id"] = normalized["order_id"]
            normalized.pop("order_id", None)

        for field in (
            "vendor_id",
            "related_doc_id",
            "order_item_id",
            "source_task_id",
            "assigned_to",
        ):
            if field in normalized:
                normalized[field] = self._to_uuid(normalized[field])

        # The legacy order_id alias and item-scoped sends both imply an order
        # document when callers omit the redundant document type.
        if (
            "related_doc_type" not in normalized
            and normalized.get("related_doc_id")
            and ("order_id" in data or normalized.get("order_item_id") is not None)
        ):
            normalized["related_doc_type"] = "order"
        if "related_doc_id" in normalized and not normalized["related_doc_id"]:
            normalized["related_doc_id"] = None
        if "order_item_id" in normalized and not normalized["order_item_id"]:
            normalized["order_item_id"] = None

        for field in ("quantity", "unit_price", "total_amount", "paid_amount", "unpaid_amount"):
            if field in normalized and normalized[field] is not None:
                normalized[field] = self._to_decimal(normalized[field])
        for field in ("expected_at", "completed_at"):
            if field in normalized and isinstance(normalized[field], str) and normalized[field]:
                normalized[field] = datetime.fromisoformat(normalized[field])
        return normalized

    async def _validate_order_item_link(
        self,
        related_doc_id: UUID | None,
        related_doc_type: str | None,
        order_item_id: UUID | None,
        *,
        allow_inactive: bool = False,
        order=None,
        for_update: bool = False,
    ):
        """Validate that an item belongs to the selected, active order."""
        if order_item_id is None:
            return None
        if related_doc_type != "order":
            raise ValueError("订单明细只能关联订单，报价单外协不能绑定订单明细")
        if related_doc_id is None:
            raise ValueError("绑定订单明细时必须同时选择订单")

        from app.models.business_document import BusinessDocument, BusinessDocumentItem

        if order is None:
            order = await self.db.get(BusinessDocument, related_doc_id)
        if (
            not order
            or getattr(order, "doc_type", None) != "order"
            or getattr(order, "deleted_at", None) is not None
        ):
            raise ValueError("所选订单不存在或已删除")
        if for_update:
            item_result = await self.db.execute(
                select(BusinessDocumentItem)
                .where(BusinessDocumentItem.id == order_item_id)
                .with_for_update()
            )
            item = item_result.scalar_one_or_none()
        else:
            item = await self.db.get(BusinessDocumentItem, order_item_id)
        if not item:
            raise ValueError("订单明细不存在")
        if getattr(item, "document_id", None) != related_doc_id:
            raise ValueError("订单明细不属于所选订单")
        lifecycle_status = getattr(item, "lifecycle_status", None)
        if not allow_inactive and lifecycle_status not in (None, "active"):
            raise ValueError("订单明细已作废，不能发送新的外协任务")
        return item

    async def _validate_source_task_link(
        self,
        related_doc_id: UUID | None,
        related_doc_type: str | None,
        source_task_type: str | None,
        source_task_id: UUID | None,
    ) -> None:
        """Validate known internal-task references and their parent order."""
        if source_task_type is None and source_task_id is None:
            return
        if not source_task_type or source_task_id is None:
            raise ValueError("来源内部任务类型和编号必须同时提供")
        if related_doc_type != "order" or related_doc_id is None:
            raise ValueError("来源内部任务必须关联订单")

        from app.models.task import DesignTask, InstallationTask, ProductionTask

        model_map = {
            "design": DesignTask,
            "production": ProductionTask,
            "installation": InstallationTask,
        }
        model = model_map.get(source_task_type)
        if model is None:
            return
        source_task = await self.db.get(model, source_task_id)
        if not source_task:
            raise ValueError(f"来源任务不存在（{source_task_type}）")
        source_order_id = getattr(source_task, "document_id", None)
        if source_order_id != related_doc_id:
            raise ValueError("来源内部任务不属于所选订单")

    async def _get_active_order(self, order_id: UUID):
        from app.models.business_document import BusinessDocument

        order = await self.db.get(BusinessDocument, order_id)
        if (
            not order
            or getattr(order, "doc_type", None) != "order"
            or getattr(order, "deleted_at", None) is not None
        ):
            raise ValueError("订单不存在或已删除")
        return order

    async def list_order_items_for_dropdown(self, order_id: UUID) -> list[dict]:
        """Return active items for the global external-task form."""
        await self._get_active_order(order_id)
        from app.models.business_document import BusinessDocumentItem

        result = await self.db.execute(
            select(BusinessDocumentItem)
            .where(
                BusinessDocumentItem.document_id == order_id,
                BusinessDocumentItem.lifecycle_status == "active",
            )
            .order_by(BusinessDocumentItem.sort_order, BusinessDocumentItem.created_at)
        )
        return [
            {
                "id": str(item.id),
                "label": f"{item.sort_order + 1}. {item.item_name} × {self._to_decimal(item.quantity):g}{item.unit or ''}",
                "item_name": item.item_name,
                "quantity": float(self._to_decimal(item.quantity)),
                "unit": item.unit,
                "group_name": item.group_name,
                "sort_order": item.sort_order,
            }
            for item in result.scalars().all()
        ]

    async def get_order_item_summary(
        self,
        order_id: UUID,
        *,
        task_type: str | None = None,
        source_task_type: str | None = None,
        source_task_id: UUID | None = None,
    ) -> dict:
        """Build the current task's item allocation view for one order."""
        order = await self._get_active_order(order_id)
        if source_task_id is not None and not source_task_type:
            raise ValueError("筛选来源任务时必须提供来源任务类型")

        from app.models.business_document import BusinessDocumentItem

        item_result = await self.db.execute(
            select(BusinessDocumentItem)
            .where(
                BusinessDocumentItem.document_id == order_id,
                BusinessDocumentItem.lifecycle_status == "active",
            )
            .order_by(BusinessDocumentItem.sort_order, BusinessDocumentItem.created_at)
        )
        items = list(item_result.scalars().all())

        task_query = select(OutsourceTask).where(
            OutsourceTask.related_doc_id == order_id,
            OutsourceTask.related_doc_type == "order",
            OutsourceTask.order_item_id.isnot(None),
            OutsourceTask.deleted_at.is_(None),
            OutsourceTask.status != "cancelled",
        )
        if task_type:
            task_query = task_query.where(OutsourceTask.task_type == task_type)
        if source_task_type:
            task_query = task_query.where(OutsourceTask.source_task_type == source_task_type)
        if source_task_id:
            task_query = task_query.where(OutsourceTask.source_task_id == source_task_id)
        task_result = await self.db.execute(task_query)
        tasks = [
            task for task in task_result.scalars().all()
            if getattr(task, "deleted_at", None) is None and task.status != "cancelled"
        ]

        by_item: dict[UUID, list] = {}
        for task in tasks:
            if task.order_item_id is not None:
                by_item.setdefault(task.order_item_id, []).append(task)

        def item_status(item, item_tasks: list) -> str:
            if getattr(item, "lifecycle_status", "active") not in (None, "active"):
                return "已作废"
            if not item_tasks:
                return "未外协"
            quantity = self._to_decimal(item.quantity)
            allocated = sum((self._to_decimal(t.quantity) for t in item_tasks), Decimal("0"))
            if allocated < quantity:
                return "部分外协"
            statuses = {t.status for t in item_tasks}
            if statuses and statuses.issubset({"completed", "settled"}):
                return "已完成"
            if "in_progress" in statuses:
                return "进行中"
            return "待处理"

        summary_items = []
        for item in items:
            item_tasks = by_item.get(item.id, [])
            item_quantity = self._to_decimal(item.quantity)
            allocated = sum(
                (self._to_decimal(task.quantity) for task in item_tasks),
                Decimal("0"),
            )
            planned_amount = sum(
                (self._to_money(task.total_amount) for task in item_tasks),
                Decimal("0"),
            )
            recognized_cost = sum(
                (
                    self._to_money(task.total_amount)
                    for task in item_tasks
                    if task.status in {"completed", "settled"}
                ),
                Decimal("0"),
            )
            remaining = max(item_quantity - allocated, Decimal("0"))
            active = getattr(item, "lifecycle_status", "active") in (None, "active")
            requires_reason = bool(item_tasks) and allocated >= item_quantity
            summary_items.append(
                {
                    "id": str(item.id),
                    "item_name": item.item_name,
                    "quantity": float(item_quantity),
                    "unit": item.unit,
                    "group_name": item.group_name,
                    "sort_order": item.sort_order,
                    "lifecycle_status": getattr(item, "lifecycle_status", "active"),
                    "allocated_quantity": float(allocated),
                    "remaining_quantity": float(remaining),
                    "planned_amount": float(planned_amount),
                    "recognized_cost": float(recognized_cost),
                    "active_task_count": len(item_tasks),
                    "status": item_status(item, item_tasks),
                    "can_send": active,
                    "requires_reason": requires_reason,
                    "block_reason": "订单明细已作废，不能发送外协" if not active else None,
                }
            )

        order_level_tasks = await self.db.execute(
            select(OutsourceTask).where(
                OutsourceTask.related_doc_id == order_id,
                OutsourceTask.related_doc_type == "order",
                OutsourceTask.order_item_id.is_(None),
                OutsourceTask.deleted_at.is_(None),
                OutsourceTask.status != "cancelled",
            )
        )
        order_level = [
            task for task in order_level_tasks.scalars().all()
            if getattr(task, "deleted_at", None) is None and task.status != "cancelled"
        ]
        if task_type:
            order_level = [task for task in order_level if task.task_type == task_type]
        if source_task_type:
            order_level = [task for task in order_level if task.source_task_type == source_task_type]
        if source_task_id:
            order_level = [task for task in order_level if task.source_task_id == source_task_id]

        return {
            "order_id": str(order.id),
            "order_no": order.doc_no,
            "project_name": order.project_name,
            "task_type": task_type,
            "source_task_type": source_task_type,
            "source_task_id": str(source_task_id) if source_task_id else None,
            "items": summary_items,
            "order_level_task_count": len(order_level),
            "order_level_planned_amount": float(
                sum((self._to_money(task.total_amount) for task in order_level), Decimal("0"))
            ),
            "order_level_recognized_cost": float(
                sum(
                    (
                        self._to_money(task.total_amount)
                        for task in order_level
                        if task.status in {"completed", "settled"}
                    ),
                    Decimal("0"),
                )
            ),
        }

    async def _list_item_tasks(
        self,
        order_id: UUID,
        item_id: UUID,
        *,
        task_type: str,
        source_task_type: str,
        source_task_id: UUID,
    ) -> list[OutsourceTask]:
        result = await self.db.execute(
            select(OutsourceTask).where(
                OutsourceTask.related_doc_id == order_id,
                OutsourceTask.related_doc_type == "order",
                OutsourceTask.order_item_id == item_id,
                OutsourceTask.task_type == task_type,
                OutsourceTask.source_task_type == source_task_type,
                OutsourceTask.source_task_id == source_task_id,
                OutsourceTask.deleted_at.is_(None),
                OutsourceTask.status != "cancelled",
            )
        )
        return list(result.scalars().all())

    async def send_order_item(self, order_id: UUID, item_id: UUID, data: dict) -> dict:
        """Create an external task owned by one current-order item."""
        payload = dict(data)
        task_type = payload.get("task_type")
        source_task_type = payload.get("source_task_type")
        source_task_id = self._to_uuid(payload.get("source_task_id"))
        if task_type not in ITEM_OUTSOURCE_TASK_TYPES:
            raise ValueError("订单明细外协必须选择设计、制作或安装任务类型")
        if source_task_type != task_type or source_task_id is None:
            raise ValueError("来源内部任务必须与外协任务类型一致")

        order = await self._get_active_order(order_id)
        item = await self._validate_order_item_link(
            order_id,
            "order",
            item_id,
            order=order,
            for_update=True,
        )
        await self._validate_source_task_link(
            order_id,
            "order",
            source_task_type,
            source_task_id,
        )

        existing = await self._list_item_tasks(
            order_id,
            item_id,
            task_type=task_type,
            source_task_type=source_task_type,
            source_task_id=source_task_id,
        )
        item_quantity = self._to_decimal(item.quantity)
        allocated_quantity = sum(
            (self._to_decimal(task.quantity) for task in existing),
            Decimal("0"),
        )
        remaining_quantity = max(item_quantity - allocated_quantity, Decimal("0"))
        raw_quantity = payload.get("quantity")
        quantity = remaining_quantity if raw_quantity is None else self._to_decimal(raw_quantity)
        if quantity <= 0:
            raise ValueError("该明细已没有可发送数量，请填写追加外协数量")
        remark = str(payload.get("remark") or "").strip()
        if quantity > remaining_quantity and not remark:
            raise ValueError("外协数量超过明细剩余数量，追加外协必须填写备注原因")

        create_data = {
            "vendor_id": payload.get("vendor_id"),
            "related_doc_id": order_id,
            "related_doc_type": "order",
            "order_item_id": item_id,
            "source_task_type": source_task_type,
            "source_task_id": source_task_id,
            "task_type": task_type,
            "description": payload.get("description") or item.item_name,
            "quantity": quantity,
            "unit_price": payload.get("unit_price", Decimal("0")),
            "expected_at": payload.get("expected_at"),
            "remark": remark or None,
        }
        return await self._create_task(
            create_data,
            validated_item=item,
            skip_link_validation=True,
            skip_source_validation=True,
        )

    # ── Vendor ──

    async def list_vendors(self, page: int, page_size: int, keyword: str | None = None,
                           service_type: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        vendors, total = await self.vendor_repo.list_vendors(skip, page_size, keyword, service_type)
        return [self._vendor_to_dict(v) for v in vendors], total

    async def get_vendor(self, vendor_id: UUID) -> dict | None:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            return None
        return self._vendor_to_dict(vendor)

    async def create_vendor(self, data: dict) -> dict:
        data["vendor_no"] = await generate_vendor_no(self.db)
        vendor = await self.vendor_repo.create(data)
        return self._vendor_to_dict(vendor)

    async def update_vendor(self, vendor_id: UUID, data: dict) -> dict:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("外协商不存在")
        vendor = await self.vendor_repo.update(vendor, data)
        return self._vendor_to_dict(vendor)

    async def delete_vendor(self, vendor_id: UUID) -> bool:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            return False
        await self.vendor_repo.soft_delete(vendor)
        return True

    # ── Task ──

    @classmethod
    def _parse_task_group_key(cls, group_key: str) -> dict:
        """Parse only keys emitted by the repository's grouping expression."""
        if group_key == "unlinked":
            return {"kind": "unlinked"}
        for kind, pattern in cls.GROUP_KEY_PATTERNS:
            match = pattern.fullmatch(group_key)
            if not match:
                continue
            try:
                identity = UUID(match.group(match.lastindex))
            except (TypeError, ValueError):
                break
            if kind == "source_task":
                return {
                    "kind": kind,
                    "source_task_type": match.group(1),
                    "source_task_id": identity,
                }
            if kind == "related_document":
                return {
                    "kind": kind,
                    "related_doc_type": match.group(1),
                    "related_doc_id": identity,
                }
            return {"kind": kind, "task_id": identity}
        raise ValueError("无效的外协任务分组键")

    @staticmethod
    def _row_value(row, name: str, default=None):
        if isinstance(row, dict):
            return row.get(name, default)
        mapping = getattr(row, "_mapping", None)
        if mapping is not None and name in mapping:
            return mapping[name]
        return getattr(row, name, default)

    async def _load_source_task_contexts(self, identities: list[dict]) -> dict[tuple[str, UUID], dict]:
        """Batch-load source task numbers/statuses to avoid one query per group."""
        from app.models.task import DesignTask, InstallationTask, ProductionTask

        model_map = {
            "design": (DesignTask, "design_no"),
            "production": (ProductionTask, "production_no"),
            "installation": (InstallationTask, "installation_no"),
        }
        refs: dict[str, set[UUID]] = {task_type: set() for task_type in model_map}
        for identity in identities:
            if identity.get("kind") != "source_task":
                continue
            refs[identity["source_task_type"]].add(identity["source_task_id"])

        contexts: dict[tuple[str, UUID], dict] = {}
        for task_type, ids in refs.items():
            if not ids:
                continue
            model, number_field = model_map[task_type]
            result = await self.db.execute(select(model).where(model.id.in_(ids)))
            for task in result.scalars().all():
                contexts[(task_type, task.id)] = {
                    "id": task.id,
                    "business_no": getattr(task, number_field, None),
                    "status": getattr(task, "status", None),
                    "project_name": getattr(task, "project_name", None),
                    "document_id": getattr(task, "document_id", None),
                }
        return contexts

    async def _load_document_contexts(
        self,
        identities: list[dict],
        source_contexts: dict[tuple[str, UUID], dict],
    ) -> dict[UUID, dict]:
        """Batch-load related order/quote labels used in group headers."""
        from app.models.business_document import BusinessDocument

        document_ids: set[UUID] = set()
        for identity in identities:
            if identity.get("kind") == "related_document":
                document_ids.add(identity["related_doc_id"])
        for source in source_contexts.values():
            document_id = source.get("document_id")
            if document_id:
                document_ids.add(document_id)
        if not document_ids:
            return {}

        result = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id.in_(document_ids))
        )
        return {
            document.id: {
                "id": document.id,
                "doc_no": getattr(document, "doc_no", None),
                "doc_type": getattr(document, "doc_type", None),
                "project_name": getattr(document, "project_name", None),
                "total_amount": getattr(document, "total_amount", None),
            }
            for document in result.scalars().all()
        }

    @staticmethod
    def _group_related_doc_ids(row) -> set[UUID]:
        raw_ids = OutsourceService._row_value(row, "related_doc_ids") or []
        if isinstance(raw_ids, (str, UUID)):
            raw_ids = [raw_ids]
        result = set()
        for value in raw_ids:
            try:
                parsed = OutsourceService._to_uuid(value)
            except (TypeError, ValueError):
                parsed = None
            if parsed:
                result.add(parsed)
        return result

    def _task_group_to_dict(
        self,
        row,
        identity: dict,
        source_contexts: dict[tuple[str, UUID], dict],
        document_contexts: dict[UUID, dict],
    ) -> dict:
        group_kind = self._row_value(row, "group_kind", "unlinked")
        source_type = identity.get("source_task_type")
        source_id = identity.get("source_task_id")
        source = source_contexts.get((source_type, source_id)) if source_type and source_id else None
        related_ids = self._group_related_doc_ids(row)
        document_id = None
        document = None
        warnings = []

        if identity.get("kind") == "related_document":
            document_id = identity["related_doc_id"]
            document = document_contexts.get(document_id)
            if not document:
                warnings.append("关联单据已不存在")
        elif source:
            document_id = source.get("document_id")
            document = document_contexts.get(document_id) if document_id else None
            if document_id and not document:
                warnings.append("来源任务关联单据已不存在")
            if related_ids and document_id and any(item_id != document_id for item_id in related_ids):
                warnings.append("来源任务与外协记录的关联单据不一致")
        elif related_ids:
            # For unresolved/legacy groups, expose a document label when it is
            # unambiguous without attempting to repair the historical link.
            document_id = next(iter(related_ids)) if len(related_ids) == 1 else None
            document = document_contexts.get(document_id) if document_id else None

        if group_kind == "source_task":
            source_label = self.SOURCE_TASK_LABELS.get(source_type, "内部")
            if source:
                group_label = f"{source_label}任务 {source.get('business_no') or source_id}"
            else:
                group_label = f"{source_label}任务（来源已不存在）"
                warnings.insert(0, "来源任务已不存在，历史外协记录已保留")
        elif group_kind == "related_document":
            document_label = self.DOCUMENT_LABELS.get(
                identity.get("related_doc_type"), "关联单据"
            )
            document_number = document.get("doc_no") if document else identity.get("related_doc_id")
            group_label = f"{document_label} {document_number} · 未关联来源任务"
        elif group_kind == "unresolved_source":
            group_label = "来源任务关联不完整"
            warnings.insert(0, "来源任务关联不完整，已按单条记录隔离")
        elif group_kind == "unresolved_document":
            group_label = "关联单据关联不完整"
            warnings.insert(0, "关联单据关联不完整，已按单条记录隔离")
        else:
            group_label = "未关联任务"

        status_keys = ("pending", "in_progress", "completed", "settled", "cancelled", "other")
        status_counts = {
            key: int(self._row_value(row, f"status_{key}_count", 0) or 0)
            for key in status_keys
        }
        source_document_id = source.get("document_id") if source else None
        if source_document_id and document_id is None:
            document_id = source_document_id
            document = document_contexts.get(document_id)

        related_doc_type = document.get("doc_type") if document else None
        if related_doc_type is None and identity.get("kind") == "related_document":
            related_doc_type = identity.get("related_doc_type")
        if related_doc_type is None and source_document_id:
            related_doc_type = "order"
        related_project_name = (
            (source.get("project_name") if source else None)
            or (document.get("project_name") if document else None)
        )
        related_project_amount = (
            self._to_money(document.get("total_amount"))
            if document and document.get("total_amount") is not None
            else None
        )
        warning = "；".join(dict.fromkeys(warnings)) or None
        return {
            "group_key": self._row_value(row, "group_key"),
            "group_kind": group_kind,
            "group_label": group_label,
            "source_task_type": source_type,
            "source_task_id": str(source_id) if source_id else None,
            "source_task_no": source.get("business_no") if source else None,
            "source_task_status": source.get("status") if source else None,
            "source_task_exists": bool(source) if group_kind == "source_task" else None,
            "related_doc_type": related_doc_type,
            "related_doc_id": str(document_id) if document_id else None,
            "related_doc_no": document.get("doc_no") if document else None,
            "related_project_name": related_project_name,
            "related_project_amount": (
                float(related_project_amount) if related_project_amount is not None else None
            ),
            "consistency_warning": warning,
            "task_count": int(self._row_value(row, "task_count", 0) or 0),
            "active_task_count": int(self._row_value(row, "active_task_count", 0) or 0),
            "status_counts": status_counts,
            "planned_amount": float(self._to_money(self._row_value(row, "planned_amount", 0))),
            "recognized_cost": float(self._to_money(self._row_value(row, "recognized_cost", 0))),
            "paid_amount": float(self._to_money(self._row_value(row, "paid_amount", 0))),
            "unpaid_amount": float(self._to_money(self._row_value(row, "unpaid_amount", 0))),
        }

    async def list_task_groups(self, page: int, page_size: int, status: str | None = None,
                               vendor_id: UUID | None = None, related_doc_id: UUID | None = None,
                               source_task_type: str | None = None, source_task_id: UUID | None = None,
                               task_type: str | None = None,
                               order_item_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        rows, total = await self.task_repo.list_task_groups(
            skip,
            page_size,
            status,
            vendor_id,
            related_doc_id,
            source_task_type,
            source_task_id,
            task_type,
            order_item_id,
        )
        identities = [
            self._parse_task_group_key(self._row_value(row, "group_key"))
            for row in rows
        ]
        source_contexts = await self._load_source_task_contexts(identities)
        document_contexts = await self._load_document_contexts(identities, source_contexts)
        return [
            self._task_group_to_dict(row, identity, source_contexts, document_contexts)
            for row, identity in zip(rows, identities)
        ], total

    async def list_task_group_tasks(self, group_key: str, page: int, page_size: int,
                                    status: str | None = None,
                                    vendor_id: UUID | None = None,
                                    related_doc_id: UUID | None = None,
                                    source_task_type: str | None = None,
                                    source_task_id: UUID | None = None,
                                    task_type: str | None = None,
                                    order_item_id: UUID | None = None) -> tuple[list, int]:
        identity = self._parse_task_group_key(group_key)
        if identity.get("kind") == "source_task":
            if source_task_type and source_task_type != identity["source_task_type"]:
                raise ValueError("分组与来源任务类型筛选不一致")
            if source_task_id and source_task_id != identity["source_task_id"]:
                raise ValueError("分组与来源任务筛选不一致")
        elif identity.get("kind") == "related_document":
            if source_task_type or source_task_id:
                raise ValueError("单据兜底组不能使用来源任务筛选")
            if related_doc_id and related_doc_id != identity["related_doc_id"]:
                raise ValueError("分组与订单筛选不一致")
        skip = (page - 1) * page_size
        tasks, total = await self.task_repo.list_task_group_tasks(
            group_key,
            skip,
            page_size,
            status,
            vendor_id,
            related_doc_id,
            source_task_type,
            source_task_id,
            task_type,
            order_item_id,
        )
        result = []
        for task in tasks:
            vendor_name = await self._task_vendor_name(task)
            project_name = await self._related_project_name(task.related_doc_id, task.related_doc_type)
            result.append(self._task_to_dict(task, vendor_name, project_name))
        return result, total

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         vendor_id: UUID | None = None, related_doc_id: UUID | None = None,
                         source_task_type: str | None = None, source_task_id: UUID | None = None,
                         task_type: str | None = None,
                         order_item_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.task_repo.list_tasks(skip, page_size, status, vendor_id, related_doc_id,
                                                       source_task_type, source_task_id, task_type, order_item_id)
        result = []
        for t in tasks:
            vname = await self._task_vendor_name(t)
            pname = await self._related_project_name(t.related_doc_id, t.related_doc_type)
            result.append(self._task_to_dict(t, vname, pname))
        return result, total

    async def _task_vendor_name(self, task) -> str | None:
        """Load vendor name explicitly to avoid async lazy loading issues."""
        return await self._vendor_name(task.vendor_id)

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        vname = await self._task_vendor_name(task)
        pname = await self._related_project_name(task.related_doc_id, task.related_doc_type)
        return self._task_to_dict(task, vname, pname)

    async def create_task(self, data: dict) -> dict:
        return await self._create_task(data)

    async def _create_task(
        self,
        data: dict,
        *,
        validated_item=None,
        skip_link_validation: bool = False,
        skip_source_validation: bool = False,
    ) -> dict:
        normalized = self._normalize_task_data(data)
        item = validated_item
        if not skip_link_validation:
            item = await self._validate_order_item_link(
                normalized.get("related_doc_id"),
                normalized.get("related_doc_type"),
                normalized.get("order_item_id"),
            )
        if not skip_source_validation:
            await self._validate_source_task_link(
                normalized.get("related_doc_id"),
                normalized.get("related_doc_type"),
                normalized.get("source_task_type"),
                normalized.get("source_task_id"),
            )

        normalized["task_no"] = await generate_outsource_task_no(self.db)
        quantity = self._to_decimal(normalized.get("quantity", 1))
        unit_price = self._to_money(normalized.get("unit_price", 0))
        total_amount = self._to_money(quantity * unit_price)
        normalized["quantity"] = quantity
        normalized["unit_price"] = unit_price
        normalized["total_amount"] = total_amount
        normalized["paid_amount"] = Decimal("0")
        normalized["unpaid_amount"] = total_amount

        task = await self.task_repo.create(normalized)
        if item is not None:
            task.order_item = item
        vname = await self._task_vendor_name(task)
        pname = await self._related_project_name(task.related_doc_id, task.related_doc_type)
        return self._task_to_dict(task, vname, pname)

    async def update_task(self, task_id: UUID, data: dict) -> dict:
        task = await self.task_repo.get_by_id(task_id, for_update=True)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status == "cancelled":
            raise ValueError("已取消的外协任务不能编辑，请从回收站流程恢复")
        if task.status == "settled":
            raise ValueError("已结算的外协任务不能编辑")
        data = self._normalize_task_data(data)

        old_item_id = getattr(task, "order_item_id", None)
        candidate_item_id = data.get("order_item_id", old_item_id)
        item_link_changed = any(
            field in data for field in ("related_doc_id", "related_doc_type", "order_item_id")
        )
        item_changed = "order_item_id" in data and candidate_item_id != old_item_id
        paid_amount = self._to_decimal(task.paid_amount)
        if item_changed and paid_amount > 0:
            raise ValueError("已有付款的外协任务不能更换订单明细")
        if item_changed and task.status in {"completed", "settled"}:
            raise ValueError("已完成的外协任务不能更换订单明细")

        candidate_doc_id = data.get("related_doc_id", getattr(task, "related_doc_id", None))
        candidate_doc_type = data.get("related_doc_type", getattr(task, "related_doc_type", None))
        validated_item = None
        if candidate_item_id is not None and item_link_changed:
            validated_item = await self._validate_order_item_link(
                candidate_doc_id,
                candidate_doc_type,
                candidate_item_id,
            )

        candidate_source_type = data.get("source_task_type", getattr(task, "source_task_type", None))
        candidate_source_id = data.get("source_task_id", getattr(task, "source_task_id", None))
        if (
            any(field in data for field in ("source_task_type", "source_task_id"))
            or item_link_changed
        ):
            await self._validate_source_task_link(
                candidate_doc_id,
                candidate_doc_type,
                candidate_source_type,
                candidate_source_id,
            )
        if (
            data.get("vendor_id")
            and UUID(str(data["vendor_id"])) != task.vendor_id
            and paid_amount > 0
        ):
            raise ValueError("已有付款的外协任务不能更换供应商")
        if "status" in data:
            ensure_transition(
                OUTSOURCE_TASK_WORKFLOW,
                task.status,
                data["status"],
            )
            if data["status"] == "completed":
                data["completed_at"] = datetime.now()
                if Decimal(str(task.unpaid_amount or 0)) == 0:
                    data["status"] = "settled"
        # Recalculate total if price or quantity changed
        if "unit_price" in data:
            price = self._to_money(data["unit_price"])
            qty = self._to_decimal(data.get("quantity", task.quantity))
            data["total_amount"] = self._to_money(qty * price)
        elif "quantity" in data:
            qty = self._to_decimal(data["quantity"])
            price = self._to_money(task.unit_price)
            data["total_amount"] = self._to_money(qty * price)
        if "total_amount" in data:
            total_amount = self._to_money(data["total_amount"])
            if total_amount < paid_amount:
                raise ValueError("任务总金额不能低于已付金额")
            data["total_amount"] = total_amount
            data["unpaid_amount"] = total_amount - paid_amount
        task = await self.task_repo.update(task, data)
        if item_link_changed:
            task.order_item = validated_item if candidate_item_id is not None else None
        vname = await self._task_vendor_name(task)
        pname = await self._related_project_name(task.related_doc_id, task.related_doc_type)
        return self._task_to_dict(task, vname, pname)

    # ── Payment ──

    async def list_payments(self, page: int, page_size: int, vendor_id: UUID | None = None,
                            task_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        payments, total = await self.payment_repo.list_payments(skip, page_size, vendor_id, task_id)
        result = []
        for p in payments:
            vname = await self._vendor_name(p.vendor_id)
            result.append(self._payment_to_dict(p, vname))
        return result, total

    async def create_payment(
        self,
        data: dict,
        created_by: UUID | None = None,
    ) -> dict:
        data = dict(data)
        # Convert string fields to proper types
        if data.get("paid_at"):
            from datetime import datetime as dt
            data["paid_at"] = dt.fromisoformat(data["paid_at"])
        if data.get("task_id") and not isinstance(data["task_id"], UUID):
            data["task_id"] = UUID(data["task_id"])
        if not isinstance(data["vendor_id"], UUID):
            data["vendor_id"] = UUID(data["vendor_id"])
        amount = Decimal(str(data["amount"]))
        if amount <= 0:
            raise ValueError("付款金额必须大于0")
        task = None
        if data.get("task_id"):
            task = await self.task_repo.get_by_id(
                data["task_id"],
                for_update=True,
            )
            if not task:
                raise ValueError("外协任务不存在")
            if task.status == "cancelled":
                raise ValueError("已取消的外协任务不能付款")
            if task.vendor_id != data["vendor_id"]:
                raise ValueError("付款供应商与外协任务不一致")
            unpaid_amount = Decimal(str(task.unpaid_amount or 0))
            if amount > unpaid_amount:
                raise ValueError(f"付款金额超过任务未付金额 {unpaid_amount:.2f} 元")
        data["payment_no"] = await generate_outsource_payment_no(self.db)
        data["created_by"] = created_by
        payment = await self.payment_repo.create(data)
        if task:
            task.paid_amount = float(Decimal(str(task.paid_amount or 0)) + amount)
            task.unpaid_amount = float(
                Decimal(str(task.total_amount or 0))
                - Decimal(str(task.paid_amount))
            )
            if task.unpaid_amount == 0 and task.status == "completed":
                task.status = "settled"
            await self.db.flush()
        vname = await self._vendor_name(payment.vendor_id)
        return self._payment_to_dict(payment, vname)

    async def _update_task_paid_amounts(self, task_id: UUID) -> None:
        """根据所有付款记录重新计算任务的已付/未付金额"""
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.coalesce(func.sum(OutsourcePayment.amount), 0))
            .where(OutsourcePayment.task_id == task_id)
        )
        total_paid = float(result.scalar())
        task = await self.task_repo.get_by_id(task_id)
        if task:
            task.paid_amount = total_paid
            task.unpaid_amount = max(0, float(task.total_amount) - total_paid)
            await self.db.flush()

    async def get_task_payment_summary(self, task_id: UUID) -> dict | None:
        """获取任务付款摘要：总金额、已付、未付、付款明细"""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        from sqlalchemy import select
        result = await self.db.execute(
            select(OutsourcePayment).where(OutsourcePayment.task_id == task_id)
            .order_by(OutsourcePayment.created_at.desc())
        )
        payments = result.scalars().all()
        vname = await self._vendor_name(task.vendor_id)
        pname = await self._related_project_name(task.related_doc_id, task.related_doc_type)
        return {
            "task_id": str(task.id),
            "task_no": task.task_no,
            "vendor_id": str(task.vendor_id),
            "vendor_name": vname,
            "related_project_name": pname,
            "total_amount": float(task.total_amount),
            "paid_amount": float(task.paid_amount),
            "unpaid_amount": float(task.unpaid_amount),
            "payments": [
                {
                    "id": str(p.id),
                    "payment_no": p.payment_no,
                    "amount": float(p.amount),
                    "payment_method": p.payment_method,
                    "payee_company_name": p.payee_company_name,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    "remark": p.remark,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
        }

    async def _vendor_name(self, vendor_id: UUID) -> str | None:
        result = await self.db.execute(select(OutsourceVendor.name).where(OutsourceVendor.id == vendor_id))
        return result.scalar_one_or_none()

    async def _related_project_name(self, doc_id: UUID | None, doc_type: str | None) -> str | None:
        if not doc_id or not doc_type:
            return None
        from app.models.business_document import BusinessDocument
        result = await self.db.execute(
            select(BusinessDocument.project_name).where(BusinessDocument.id == doc_id)
        )
        return result.scalar_one_or_none()


    # ── Recycle Bin ──

    async def list_deleted(self, page: int, page_size: int) -> tuple[list, int]:
        """列出已删除的外协任务（回收站）"""
        skip = (page - 1) * page_size
        tasks, total = await self.task_repo.list_deleted_tasks(skip, page_size)
        result = []
        for t in tasks:
            vname = await self._task_vendor_name(t)
            pname = await self._related_project_name(t.related_doc_id, t.related_doc_type)
            result.append(self._task_to_dict(t, vname, pname))
        return result, total

    async def restore_task(self, task_id: UUID) -> dict:
        """从回收站恢复外协任务"""
        task = await self.task_repo.get_deleted_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在或未被删除")
        await self.task_repo.restore(task)
        # 删除时付款已级联清除，恢复后按现存付款记录重算已付/未付
        count, total = await self.payment_repo.payment_totals(task_id)
        task.paid_amount = total
        task.unpaid_amount = max(0.0, float(task.total_amount or 0) - total)
        await self.db.flush()
        vname = await self._task_vendor_name(task)
        pname = await self._related_project_name(task.related_doc_id, task.related_doc_type)
        return self._task_to_dict(task, vname, pname)

    # ── Helpers ──

    def _vendor_to_dict(self, v) -> dict:
        return {
            "id": str(v.id), "vendor_no": v.vendor_no,
            "name": v.name, "contact_person": v.contact_person,
            "phone": v.phone, "address": v.address,
            "service_type": v.service_type, "coop_rating": v.coop_rating,
            "remark": v.remark, "is_active": v.is_active,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }

    def _task_to_dict(self, t, vendor_name: str | None = None, related_project_name: str | None = None) -> dict:
        order_item = (
            getattr(t, "order_item", None)
            if t.related_doc_type == "order" and t.order_item_id
            else None
        )
        order_item_name = getattr(order_item, "item_name", None) if order_item else None
        if not isinstance(order_item_name, str):
            order_item_name = None
        return {
            "id": str(t.id), "task_no": t.task_no,
            "vendor_id": str(t.vendor_id),
            "vendor_name": vendor_name,
            "related_doc_id": str(t.related_doc_id) if t.related_doc_id else None,
            "related_doc_type": t.related_doc_type,
            "related_project_name": related_project_name,
            "order_id": str(t.related_doc_id) if t.related_doc_id else None,
            "order_item_id": str(t.order_item_id) if t.order_item_id else None,
            "order_item_name": order_item_name,
            "source_task_type": t.source_task_type,
            "source_task_id": str(t.source_task_id) if t.source_task_id else None,
            "task_type": t.task_type,
            "description": t.description,
            "quantity": float(self._to_decimal(t.quantity)),
            "unit_price": float(self._to_decimal(t.unit_price)),
            "total_amount": float(self._to_decimal(t.total_amount)),
            "paid_amount": float(self._to_decimal(t.paid_amount)),
            "unpaid_amount": float(self._to_decimal(t.unpaid_amount)),
            "status": t.status,
            "expected_at": t.expected_at.isoformat() if t.expected_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "remark": t.remark,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
        }

    def _payment_to_dict(self, p, vendor_name: str | None = None) -> dict:
        return {
            "id": str(p.id), "payment_no": p.payment_no,
            "vendor_id": str(p.vendor_id),
            "vendor_name": vendor_name,
            "task_id": str(p.task_id) if p.task_id else None,
            "amount": float(p.amount),
            "payment_method": p.payment_method,
                    "payee_company_name": p.payee_company_name,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "remark": p.remark,
            "created_by": str(p.created_by) if p.created_by else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    # ── Cancel Task (admin only) ──

    async def cancel_task(self, task_id: UUID) -> dict:
        task = await self.task_repo.get_by_id(task_id, for_update=True)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status in ("completed", "settled", "cancelled"):
            raise ValueError(f"当前状态「{task.status}」不允许取消")
        if Decimal(str(task.paid_amount or 0)) > 0:
            raise ValueError("该外协任务已有付款，不能取消")
        task.status = "cancelled"
        await self.db.flush()
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    # ── Revert Task (admin only: completed → in_progress) ──

    async def revert_task(self, task_id: UUID) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status != "completed":
            raise ValueError(f"当前状态「{task.status}」不允许退回，仅已完成的任务可以退回")
        task.status = "in_progress"
        task.completed_at = None
        await self.db.flush()
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    # ── Delete Task (admin only, soft delete + cascade payments) ──

    async def delete_task(self, task_id: UUID) -> dict:
        """删除外协任务：任务软删除进回收站，关联付款记录一并删除。

        返回删除摘要 {task_id, task_no, deleted_payment_count, deleted_payment_total}。
        """
        task = await self.task_repo.get_by_id(task_id, for_update=True)
        if not task:
            raise ValueError("外协任务不存在")
        count, total = await self.payment_repo.payment_totals(task_id)
        if count:
            await self.payment_repo.delete_by_task(task_id)
        await self.task_repo.soft_delete(task)
        return {
            "task_id": str(task.id),
            "task_no": task.task_no,
            "deleted_payment_count": count,
            "deleted_payment_total": total,
        }
