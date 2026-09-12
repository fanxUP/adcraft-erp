"""Read-only completed-project projection for the project boards.

The active task queue intentionally drops terminal tasks.  This service keeps
the completed board separate from that queue while reusing the same ownership,
stage-permission and price-field rules.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping
from uuid import UUID

from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    PERM_DESIGN_TASK_READ,
    PERM_INSTALLATION_TASK_READ,
    PERM_ORDER_VIEW_PRICE,
    PERM_PRODUCTION_TASK_READ,
    PERM_SYSTEM_SUPER_ADMIN,
    PERM_TASK_COMPLETION_VIEW_ALL,
    user_has_permission,
)
from app.models.business_document import (
    BusinessDocument,
    BusinessDocumentItem,
    BusinessDocumentStatusLog,
)
from app.models.employee import Employee
from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.task_item_status_log import TaskItemStatusLog
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.schemas.task import (
    CompletedProjectCard,
    CompletedProjectDetail,
    TaskType,
)
from app.services.order_task_assignment_service import task_visibility_clause
from app.services.task_completion_metrics_service import (
    CompletionEvent,
    TASK_COMPLETED_STATUSES,
    TASK_NUMBER_FIELDS,
    TASK_TYPES,
)


TASK_MODELS = {
    "design": DesignTask,
    "production": ProductionTask,
    "installation": InstallationTask,
}
TASK_READ_PERMISSIONS = {
    "design": PERM_DESIGN_TASK_READ,
    "production": PERM_PRODUCTION_TASK_READ,
    "installation": PERM_INSTALLATION_TASK_READ,
}
COMPLETED_PROJECT_NOT_FOUND_MESSAGE = "完成项目不存在或当前账号无权查看"


class CompletedProjectNotFound(ValueError):
    """A completed project is missing or outside the current viewer scope."""


def _iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _number(value: Decimal | int | float | str | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _value(source: object, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _format_numeric(value: Decimal | int | float | str) -> str:
    try:
        number = Decimal(str(value))
        if number == number.to_integral_value():
            return str(int(number))
        return format(number.normalize(), "f")
    except (ArithmeticError, TypeError, ValueError):
        return str(value)


def _format_item_specification(item: object) -> str | None:
    """Format dimensions for the completed-detail table without price data."""
    stored_specification = _value(item, "specification")
    if stored_specification:
        return str(stored_specification)

    parts: list[str] = []
    for field_name, unit_name in (
        ("length", "length_unit"),
        ("width", "width_unit"),
        ("height", "height_unit"),
    ):
        raw_value = _value(item, field_name)
        if raw_value in (None, ""):
            continue
        try:
            if Decimal(str(raw_value)) <= 0:
                continue
        except (ArithmeticError, TypeError, ValueError):
            continue
        parts.append(f"{_format_numeric(raw_value)}{_value(item, unit_name) or 'm'}")
    return " × ".join(parts) or None


def _is_installation_media_attachment(attachment: object) -> bool:
    file_type = str(_value(attachment, "file_type", "") or "").lower()
    category = str(_value(attachment, "category", "") or "").lower()
    return file_type.startswith(("image/", "video/")) or category in {
        "photo",
        "video",
        "site_media",
    }


def _serialize_attachment(attachment: object) -> dict:
    return AttachmentResponse.model_validate(attachment).model_dump(
        mode="json",
        exclude_none=True,
    )


def serialize_completed_project_resources(
    task_type: str,
    tasks: Iterable[object],
    attachments: Iterable[object],
) -> dict:
    """Group already-authorized task resources without exposing other stages."""
    task_list = list(tasks)
    task_ids = {
        str(task_id)
        for task in task_list
        if (task_id := _value(task, "id")) is not None
    }
    attachments_by_task: dict[str, list[dict]] = defaultdict(list)
    related_type = f"{task_type}_task"
    for attachment in attachments:
        if _value(attachment, "related_type") != related_type:
            continue
        related_id = _value(attachment, "related_id")
        related_key = str(related_id) if related_id is not None else ""
        if related_key not in task_ids:
            continue
        if task_type == "installation" and not _is_installation_media_attachment(attachment):
            continue
        attachments_by_task[related_key].append(_serialize_attachment(attachment))

    number_field = TASK_NUMBER_FIELDS[task_type]
    task_rows = []
    for task in task_list:
        task_id = _value(task, "id")
        if task_id is None:
            continue
        task_rows.append(
            {
                "task_id": str(task_id),
                "task_no": _value(task, number_field),
                "attachments": attachments_by_task.get(str(task_id), []),
            }
        )

    return {
        "task_type": task_type,
        "task_label": {"design": "设计", "production": "制作", "installation": "安装"}[task_type],
        "task_count": len(task_rows),
        "attachment_count": sum(len(row["attachments"]) for row in task_rows),
        "tasks": task_rows,
    }


def _event_project_groups(events: Iterable[CompletionEvent]) -> dict[UUID, list[CompletionEvent]]:
    groups: dict[UUID, list[CompletionEvent]] = defaultdict(list)
    for event in events:
        groups[event.document_id].append(event)
    return groups


def _scope_events(
    events: Iterable[CompletionEvent],
    *,
    scope: str,
    owner_user_id: UUID | None,
) -> list[CompletionEvent]:
    rows = list(events)
    if scope != "own":
        return rows
    if owner_user_id is None:
        return []
    return [event for event in rows if event.assignee_user_id == owner_user_id]


def aggregate_completed_project_cards(
    documents: Iterable[object],
    completion_times: Mapping[UUID, datetime | None],
    events: Iterable[CompletionEvent],
    *,
    scope: str,
    include_amount: bool,
    owner_user_id: UUID | None = None,
) -> list[dict]:
    """Aggregate one card per project from already-authorized rows.

    Keeping this aggregation pure makes the employee-vs-admin boundary easy to
    test and prevents the UI from reimplementing project deduplication.
    """
    scoped_events = _scope_events(
        events,
        scope=scope,
        owner_user_id=owner_user_id,
    )
    grouped = _event_project_groups(scoped_events)
    rows: list[dict] = []
    for document in documents:
        project_id = document.id
        if scope == "own" and project_id not in grouped:
            continue
        project_events = grouped.get(project_id, [])
        stages = sorted(
            {event.task_type for event in project_events},
            key=TASK_TYPES.index,
        )
        row = {
            "kind": "project",
            "project_id": str(project_id),
            "project_no": document.doc_no,
            "project_name": document.project_name,
            "customer_name": document.customer_name,
            "department": document.department,
            "status": "completed",
            "completed_at": _iso_datetime(completion_times.get(project_id)),
            "completed_detail_count": len({event.order_item_id for event in project_events}),
            "completed_work_unit_count": len(project_events),
            "stages": stages,
            "scope": scope,
        }
        if include_amount:
            amount = _number(getattr(document, "total_amount", None))
            if amount is not None:
                row["total_amount"] = amount
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            row["completed_at"] is not None,
            row["completed_at"] or "",
            row["project_no"],
        ),
        reverse=True,
    )


def build_completed_project_detail(
    document: object,
    completion_time: datetime | None,
    events: Iterable[CompletionEvent],
    *,
    scope: str,
    include_amount: bool,
    owner_user_id: UUID | None = None,
    order_items: Iterable[object] | None = None,
    resources: Mapping[str, dict] | None = None,
) -> dict:
    """Build an item-centric, read-only project detail payload."""
    project_events = [event for event in events if event.document_id == document.id]
    project_events = _scope_events(
        project_events,
        scope=scope,
        owner_user_id=owner_user_id,
    )
    card = aggregate_completed_project_cards(
        [document],
        {document.id: completion_time},
        project_events,
        scope="all",
        include_amount=include_amount,
    )[0]
    card["scope"] = scope
    latest_events: dict[tuple[UUID, str], CompletionEvent] = {}
    for event in project_events:
        key = (event.order_item_id, event.task_type)
        previous = latest_events.get(key)
        if previous is None or (
            event.operated_at is not None,
            event.operated_at or datetime.min,
            str(event.id),
        ) > (
            previous.operated_at is not None,
            previous.operated_at or datetime.min,
            str(previous.id),
        ):
            latest_events[key] = event

    event_item_ids = {event.order_item_id for event in project_events}
    raw_items = list(order_items or _value(document, "items", []) or [])
    if not raw_items:
        raw_items = [
            {
                "id": item_id,
                "item_name": next(
                    (
                        event.item_name
                        for event in project_events
                        if event.order_item_id == item_id and event.item_name
                    ),
                    "未命名明细",
                ),
                "sort_order": position,
            }
            for position, item_id in enumerate(sorted(event_item_ids, key=str))
        ]

    if scope == "own":
        raw_items = [item for item in raw_items if _value(item, "id") in event_item_ids]
    raw_items.sort(key=lambda item: (_value(item, "sort_order", 0), str(_value(item, "id", ""))))

    detail_rows = []
    for item in raw_items:
        item_id = _value(item, "id")
        if item_id is None:
            continue
        stage_rows: dict[str, dict | None] = {}
        for task_type in TASK_TYPES:
            event = latest_events.get((item_id, task_type))
            stage_rows[task_type] = (
                {
                    "status": "completed",
                    "status_label": "已完成",
                    "employee_id": str(event.assignee_user_id) if event.assignee_user_id else None,
                    "employee_name": event.assignee_name or "未分配",
                    "completed_at": _iso_datetime(event.operated_at),
                    "task_id": str(event.task_id),
                    "task_no": event.task_no,
                    "source": event.source,
                }
                if event
                else None
            )
        detail_rows.append(
            {
                "kind": "detail",
                "project_id": str(document.id),
                "project_no": document.doc_no,
                "project_name": document.project_name,
                "order_item_id": str(item_id),
                "item_name": _value(item, "item_name") or "未命名明细",
                "material_process": _value(item, "material_process"),
                "specification": _format_item_specification(item),
                "quantity": _number(_value(item, "quantity")),
                "unit": _value(item, "unit"),
                "stages": stage_rows,
            }
        )
    card["items"] = detail_rows
    card["resources"] = dict(resources or {})
    return CompletedProjectDetail.model_validate(card).model_dump(
        mode="json",
        exclude_none=True,
    )


class CompletedProjectBoardService:
    def __init__(self, db: AsyncSession, viewer: User):
        self.db = db
        self.viewer = viewer
        self._resolved_scope: str | None = None
        self._resolved_owner_user_id: UUID | None = None

    @property
    def can_view_all(self) -> bool:
        return user_has_permission(self.viewer, PERM_TASK_COMPLETION_VIEW_ALL)

    @property
    def is_super_admin(self) -> bool:
        return user_has_permission(self.viewer, PERM_SYSTEM_SUPER_ADMIN)

    def allowed_task_types(self, stage: TaskType | None = None) -> list[str]:
        allowed = [
            task_type
            for task_type in TASK_TYPES
            if user_has_permission(self.viewer, TASK_READ_PERMISSIONS[task_type])
        ]
        if stage:
            return [stage] if stage in allowed else []
        return allowed

    async def _current_employee(self) -> Employee | None:
        result = await self.db.execute(
            select(Employee).where(
                Employee.user_id == self.viewer.id,
                Employee.is_active.is_(True),
                Employee.employment_status == "active",
                Employee.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _resolve_scope(self) -> tuple[str, UUID | None, bool]:
        if self.can_view_all:
            self._resolved_scope = "all"
            self._resolved_owner_user_id = None
            return "all", None, False

        employee = await self._current_employee()
        if employee is None:
            self._resolved_scope = "own"
            self._resolved_owner_user_id = None
            return "own", None, True

        self._resolved_scope = "own"
        self._resolved_owner_user_id = self.viewer.id
        return "own", self.viewer.id, False

    def ensure_project_in_scope(
        self,
        project_id: UUID,
        visible_project_ids: set[UUID],
    ) -> None:
        if project_id not in visible_project_ids:
            raise CompletedProjectNotFound(COMPLETED_PROJECT_NOT_FOUND_MESSAGE)

    def _event_visibility_clause(self, task_types: Iterable[str]):
        log = TaskItemStatusLog
        clauses = []
        for task_type in task_types:
            model = TASK_MODELS[task_type]
            clauses.append(
                and_(
                    log.task_type == task_type,
                    exists(
                        select(model.id).where(
                            model.id == log.task_id,
                            task_visibility_clause(model, self.viewer),
                        )
                    ),
                )
            )
        return or_(*clauses) if clauses else false()

    async def _load_completed_documents(
        self,
        *,
        project_id: UUID | None = None,
    ) -> list[tuple[BusinessDocument, BusinessDocumentStatusLog]]:
        status_log = BusinessDocumentStatusLog
        rank = func.row_number().over(
            partition_by=status_log.document_id,
            order_by=(status_log.operated_at.desc().nulls_last(), status_log.id.desc()),
        ).label("event_rank")
        ranked = select(status_log.id.label("event_id"), rank).subquery()
        conditions = [
            ranked.c.event_rank == 1,
            status_log.to_status == "completed",
            BusinessDocument.status == "completed",
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        ]
        if project_id is not None:
            conditions.append(BusinessDocument.id == project_id)
        result = await self.db.execute(
            select(BusinessDocument, status_log)
            .join(ranked, ranked.c.event_id == status_log.id)
            .join(BusinessDocument, BusinessDocument.id == status_log.document_id)
            .where(*conditions)
        )
        return list(result.all())

    async def _load_completion_events(
        self,
        task_types: list[str],
        *,
        owner_user_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> list[CompletionEvent]:
        if not task_types:
            return []

        log = TaskItemStatusLog
        rank = func.row_number().over(
            partition_by=(log.task_type, log.order_item_id),
            order_by=(log.operated_at.desc().nulls_last(), log.id.desc()),
        ).label("event_rank")
        ranked = select(log.id.label("event_id"), rank).subquery()
        completed_statuses = {
            status
            for task_type in task_types
            for status in TASK_COMPLETED_STATUSES[task_type]
        }
        conditions = [
            ranked.c.event_rank == 1,
            log.task_type.in_(task_types),
            log.to_status.in_(completed_statuses),
            BusinessDocument.doc_type == "order",
            BusinessDocument.status == "completed",
            BusinessDocument.deleted_at.is_(None),
            BusinessDocumentItem.lifecycle_status == "active",
            self._event_visibility_clause(task_types),
        ]
        if owner_user_id is not None:
            conditions.append(log.assignee_user_id == owner_user_id)
        if project_id is not None:
            conditions.append(log.document_id == project_id)

        result = await self.db.execute(
            select(log, BusinessDocument, BusinessDocumentItem)
            .join(ranked, ranked.c.event_id == log.id)
            .join(BusinessDocument, BusinessDocument.id == log.document_id)
            .join(BusinessDocumentItem, BusinessDocumentItem.id == log.order_item_id)
            .where(*conditions)
        )
        return [
            CompletionEvent(
                id=log_row.id,
                task_type=log_row.task_type,
                task_id=log_row.task_id,
                document_id=log_row.document_id,
                order_item_id=log_row.order_item_id,
                to_status=log_row.to_status,
                operated_at=log_row.operated_at,
                assignee_user_id=log_row.assignee_user_id,
                source=log_row.source,
                project_no=document.doc_no,
                project_name=document.project_name,
                item_name=item.item_name,
            )
            for log_row, document, item in result.all()
        ]

    async def _prepare_events(self, events: list[CompletionEvent]) -> None:
        task_ids_by_type: dict[str, set[UUID]] = defaultdict(set)
        for event in events:
            task_ids_by_type[event.task_type].add(event.task_id)
        for task_type, task_ids in task_ids_by_type.items():
            model = TASK_MODELS[task_type]
            number_field = getattr(model, TASK_NUMBER_FIELDS[task_type])
            result = await self.db.execute(
                select(model.id, number_field).where(model.id.in_(task_ids))
            )
            numbers = {task_id: task_no for task_id, task_no in result.all()}
            for event in events:
                if event.task_type == task_type:
                    event.task_no = numbers.get(event.task_id)

        user_ids = {
            event.assignee_user_id
            for event in events
            if event.assignee_user_id is not None
        }
        if not user_ids:
            return
        result = await self.db.execute(
            select(Employee.user_id, Employee.name).where(
                Employee.user_id.in_(user_ids),
                Employee.deleted_at.is_(None),
            )
        )
        names = {user_id: name for user_id, name in result.all()}
        for event in events:
            event.assignee_name = names.get(event.assignee_user_id)

    async def _load_active_order_items(self, project_id: UUID) -> list[BusinessDocumentItem]:
        result = await self.db.execute(
            select(BusinessDocumentItem)
            .where(
                BusinessDocumentItem.document_id == project_id,
                BusinessDocumentItem.lifecycle_status == "active",
            )
            .order_by(BusinessDocumentItem.sort_order, BusinessDocumentItem.id)
        )
        return list(result.scalars().all())

    async def _load_projection(
        self,
        *,
        stage: TaskType | None = None,
        project_id: UUID | None = None,
    ) -> tuple[
        str,
        UUID | None,
        bool,
        list[tuple[BusinessDocument, BusinessDocumentStatusLog]],
        list[CompletionEvent],
    ]:
        scope, owner_user_id, no_data = await self._resolve_scope()
        if no_data:
            return scope, owner_user_id, no_data, [], []

        task_types = self.allowed_task_types(stage)
        documents = await self._load_completed_documents(project_id=project_id)
        events = await self._load_completion_events(
            task_types,
            owner_user_id=owner_user_id,
            project_id=project_id,
        )
        await self._prepare_events(events)

        visible_project_ids = {event.document_id for event in events}
        if scope == "own" or not self.is_super_admin:
            documents = [
                (document, status_log)
                for document, status_log in documents
                if document.id in visible_project_ids
            ]
        return scope, owner_user_id, no_data, documents, events

    async def get_projects(
        self,
        *,
        page: int,
        page_size: int,
        stage: TaskType | None = None,
    ) -> tuple[list[dict], int]:
        if page < 1 or page_size < 1 or page_size > 200:
            raise ValueError("分页参数不正确")
        scope, owner_user_id, no_data, document_rows, events = await self._load_projection(stage=stage)
        if no_data:
            return [], 0
        documents = [document for document, _ in document_rows]
        completion_times = {
            document.id: status_log.operated_at
            for document, status_log in document_rows
        }
        rows = aggregate_completed_project_cards(
            documents,
            completion_times,
            events,
            scope=scope,
            owner_user_id=owner_user_id,
            include_amount=user_has_permission(self.viewer, PERM_ORDER_VIEW_PRICE),
        )
        total = len(rows)
        offset = (page - 1) * page_size
        return [
            CompletedProjectCard.model_validate(row).model_dump(
                mode="json",
                exclude_none=True,
            )
            for row in rows[offset : offset + page_size]
        ], total

    async def get_project(self, project_id: UUID) -> dict:
        scope, owner_user_id, no_data, document_rows, events = await self._load_projection(
            project_id=project_id,
        )
        if no_data or not document_rows:
            raise CompletedProjectNotFound(COMPLETED_PROJECT_NOT_FOUND_MESSAGE)
        visible_project_ids = {document.id for document, _ in document_rows}
        self.ensure_project_in_scope(project_id, visible_project_ids)
        document, status_log = document_rows[0]
        if scope == "own" and not any(event.document_id == project_id for event in events):
            raise CompletedProjectNotFound(COMPLETED_PROJECT_NOT_FOUND_MESSAGE)
        if not self.is_super_admin and not events:
            raise CompletedProjectNotFound(COMPLETED_PROJECT_NOT_FOUND_MESSAGE)
        order_items = await self._load_active_order_items(document.id)
        return build_completed_project_detail(
            document,
            status_log.operated_at,
            events,
            scope=scope,
            owner_user_id=owner_user_id,
            include_amount=user_has_permission(self.viewer, PERM_ORDER_VIEW_PRICE),
            order_items=order_items,
        )
