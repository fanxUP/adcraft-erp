"""Completion metrics for the operating cockpit.

This service is intentionally separate from the financial ``ReportService``.
It owns one non-financial completion vocabulary, one employee scope rule and
one latest-event calculation for all cockpit consumers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
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
from app.services.order_task_assignment_service import task_visibility_clause


BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
TASK_TYPES = ("design", "production", "installation")
TASK_TYPE_LABELS = {
    "design": "设计",
    "production": "制作",
    "installation": "安装",
}
TASK_COMPLETED_STATUSES = {
    "design": frozenset({"confirmed", "completed"}),
    "production": frozenset({"completed"}),
    "installation": frozenset({"completed"}),
}
TASK_MODELS = {
    "design": DesignTask,
    "production": ProductionTask,
    "installation": InstallationTask,
}
TASK_NUMBER_FIELDS = {
    "design": "design_no",
    "production": "production_no",
    "installation": "installation_no",
}


class TaskCompletionAccessError(PermissionError):
    """The caller attempted to widen a personal completion scope."""


class TaskCompletionEmployeeNotFound(ValueError):
    """An administrator selected an employee that cannot be resolved."""


@dataclass(slots=True)
class CompletionEvent:
    id: UUID
    task_type: str
    task_id: UUID
    document_id: UUID
    order_item_id: UUID
    to_status: str
    operated_at: datetime | None
    assignee_user_id: UUID | None
    source: str = "live"
    project_no: str | None = None
    project_name: str | None = None
    item_name: str | None = None
    task_no: str | None = None
    assignee_name: str | None = None


def _naive_business_now() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)


def get_task_completion_period(
    period: str,
    *,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Return the Shanghai-time half-open interval for a cockpit period."""
    if period not in {"all", "month"}:
        raise ValueError("统计范围只能选择全部或当月")
    if period == "all":
        return None, None

    current = now or _naive_business_now()
    if current.tzinfo is not None:
        current = current.astimezone(BUSINESS_TIMEZONE).replace(tzinfo=None)
    start = datetime(current.year, current.month, 1)
    if current.month == 12:
        end = datetime(current.year + 1, 1, 1)
    else:
        end = datetime(current.year, current.month + 1, 1)
    return start, end


def _event_sort_key(event: CompletionEvent | object) -> tuple[bool, datetime, str]:
    operated_at = getattr(event, "operated_at", None)
    return (
        operated_at is not None,
        operated_at or datetime.min,
        str(getattr(event, "id", "")),
    )


def _select_current_completed_work_units(
    events: Iterable[CompletionEvent | object],
    *,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    owner_user_id: UUID | None = None,
    task_type: str | None = None,
) -> list[CompletionEvent | object]:
    """Select the latest current state for each ``(stage, order item)``.

    The period is applied after latest-state selection.  This is what prevents
    an old completed event from surviving a later rework event, while also
    making a detail completed before this month ineligible for the month view.
    """
    latest: dict[tuple[str, UUID], CompletionEvent | object] = {}
    for event in events:
        current_type = getattr(event, "task_type", None)
        item_id = getattr(event, "order_item_id", None)
        if current_type not in TASK_TYPES or item_id is None:
            continue
        if task_type and current_type != task_type:
            continue
        key = (current_type, item_id)
        previous = latest.get(key)
        if previous is None or _event_sort_key(event) > _event_sort_key(previous):
            latest[key] = event

    selected: list[CompletionEvent | object] = []
    for event in latest.values():
        current_type = getattr(event, "task_type")
        if getattr(event, "to_status", None) not in TASK_COMPLETED_STATUSES[current_type]:
            continue
        if owner_user_id is not None and getattr(event, "assignee_user_id", None) != owner_user_id:
            continue
        operated_at = getattr(event, "operated_at", None)
        if period_start is not None:
            if operated_at is None or operated_at < period_start:
                continue
        if period_end is not None:
            if operated_at is None or operated_at >= period_end:
                continue
        selected.append(event)

    return sorted(
        selected,
        key=lambda event: (
            getattr(event, "operated_at", None) is not None,
            getattr(event, "operated_at", None) or datetime.min,
            str(getattr(event, "project_no", "")),
            str(getattr(event, "item_name", "")),
        ),
        reverse=True,
    )


def _iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_completion_detail(
    *,
    project_id: UUID,
    project_no: str,
    project_name: str,
    item_id: UUID,
    item_name: str,
    task_type: str,
    task_id: UUID,
    task_no: str | None,
    assignee_user_id: UUID | None,
    assignee_name: str | None,
    completed_at: datetime | None,
    source: str = "live",
) -> dict:
    """Build the non-financial detail whitelist used by the API."""
    return {
        "kind": "detail",
        "project_id": str(project_id),
        "project_no": project_no,
        "project_name": project_name,
        "order_item_id": str(item_id),
        "item_name": item_name,
        "task_type": task_type,
        "task_label": TASK_TYPE_LABELS[task_type],
        "task_id": str(task_id),
        "task_no": task_no,
        "employee_id": str(assignee_user_id) if assignee_user_id else None,
        "employee_name": assignee_name or "未分配",
        "completed_at": _iso_datetime(completed_at),
        "status": "已完成",
        "source": source,
    }


def _zero_stats() -> dict:
    return {
        "completed_project_count": 0,
        "completed_work_unit_count": 0,
        "stage_breakdown": {task_type: 0 for task_type in TASK_TYPES},
    }


def _stats(events: Iterable[CompletionEvent | object]) -> dict:
    events = list(events)
    result = _zero_stats()
    result["completed_project_count"] = len({getattr(event, "document_id") for event in events})
    result["completed_work_unit_count"] = len(events)
    for event in events:
        task_type = getattr(event, "task_type")
        result["stage_breakdown"][task_type] += 1
    return result


def _employee_payload(employee: Employee | None, *, user_id: UUID | None = None) -> dict | None:
    if employee is None and user_id is None:
        return None
    return {
        "employee_id": str(employee.id) if employee else None,
        "user_id": str(employee.user_id if employee else user_id) if (employee or user_id) else None,
        "employee_no": employee.employee_no if employee else None,
        "name": employee.name if employee else "未绑定员工",
        "is_active": bool(employee.is_active) if employee else False,
        "employment_status": employee.employment_status if employee else None,
    }


class TaskCompletionMetricsService:
    def __init__(self, db: AsyncSession, viewer):
        self.db = db
        self.viewer = viewer

    @property
    def can_view_all(self) -> bool:
        return user_has_permission(self.viewer, PERM_TASK_COMPLETION_VIEW_ALL)

    async def _current_employee(self) -> Employee | None:
        viewer_id = getattr(self.viewer, "id", None)
        if viewer_id is None:
            return None
        result = await self.db.execute(
            select(Employee).where(
                Employee.user_id == viewer_id,
                Employee.is_active.is_(True),
                Employee.employment_status == "active",
                Employee.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _employee_by_id(self, employee_id: UUID) -> Employee:
        result = await self.db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.deleted_at.is_(None),
            )
        )
        employee = result.scalar_one_or_none()
        if employee is None:
            raise TaskCompletionEmployeeNotFound("员工不存在或已删除")
        if not employee.user_id:
            raise TaskCompletionEmployeeNotFound("该员工未绑定登录账号，暂无可查询的完成统计")
        return employee

    async def _resolve_scope(self, employee_id: UUID | None) -> dict:
        current_employee = await self._current_employee()
        if self.can_view_all:
            target_employee = await self._employee_by_id(employee_id) if employee_id else None
            return {
                "scope": "all",
                "current_employee": current_employee,
                "target_employee": target_employee,
                "owner_user_id": target_employee.user_id if target_employee else None,
                "no_data": False,
            }

        if employee_id is not None and (
            current_employee is None or employee_id != current_employee.id
        ):
            raise TaskCompletionAccessError("只能查看当前登录员工自己的完成统计")
        return {
            "scope": "own",
            "current_employee": current_employee,
            "target_employee": current_employee,
            "owner_user_id": getattr(self.viewer, "id", None),
            "no_data": current_employee is None,
        }

    def _event_visibility_clause(self):
        log = TaskItemStatusLog
        return or_(
            and_(
                log.task_type == "design",
                exists(
                    select(DesignTask.id).where(
                        DesignTask.id == log.task_id,
                        task_visibility_clause(DesignTask, self.viewer),
                    )
                ),
            ),
            and_(
                log.task_type == "production",
                exists(
                    select(ProductionTask.id).where(
                        ProductionTask.id == log.task_id,
                        task_visibility_clause(ProductionTask, self.viewer),
                    )
                ),
            ),
            and_(
                log.task_type == "installation",
                exists(
                    select(InstallationTask.id).where(
                        InstallationTask.id == log.task_id,
                        task_visibility_clause(InstallationTask, self.viewer),
                    )
                ),
            ),
        )

    async def _load_latest_events(
        self,
        *,
        owner_user_id: UUID | None = None,
        task_type: str | None = None,
    ) -> list[CompletionEvent]:
        log = TaskItemStatusLog
        rank = func.row_number().over(
            partition_by=(log.task_type, log.order_item_id),
            order_by=(log.operated_at.desc().nulls_last(), log.id.desc()),
        ).label("event_rank")
        ranked = select(log.id.label("event_id"), rank).subquery()

        conditions = [
            ranked.c.event_rank == 1,
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
            BusinessDocument.status != "cancelled",
            BusinessDocumentItem.lifecycle_status == "active",
            self._event_visibility_clause(),
        ]
        if owner_user_id is not None:
            conditions.append(log.assignee_user_id == owner_user_id)
        if task_type:
            conditions.append(log.task_type == task_type)

        result = await self.db.execute(
            select(log, BusinessDocument, BusinessDocumentItem)
            .join(ranked, ranked.c.event_id == log.id)
            .join(BusinessDocument, BusinessDocument.id == log.document_id)
            .join(BusinessDocumentItem, BusinessDocumentItem.id == log.order_item_id)
            .where(*conditions)
        )
        events: list[CompletionEvent] = []
        for log_row, document, item in result.all():
            events.append(
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
            )
        return events

    async def _load_task_metadata(self, events: list[CompletionEvent]) -> None:
        by_type: dict[str, set[UUID]] = defaultdict(set)
        for event in events:
            by_type[event.task_type].add(event.task_id)

        for task_type, task_ids in by_type.items():
            model = TASK_MODELS[task_type]
            result = await self.db.execute(select(model).where(model.id.in_(task_ids)))
            number_field = TASK_NUMBER_FIELDS[task_type]
            tasks = result.scalars().all()
            task_numbers = {
                task.id: getattr(task, number_field, None)
                for task in tasks
            }
            for event in events:
                if event.task_type == task_type:
                    event.task_no = task_numbers.get(event.task_id)

    async def _load_employees(self, user_ids: set[UUID] | None = None) -> dict[UUID, Employee]:
        query = select(Employee).where(
            Employee.deleted_at.is_(None),
            Employee.user_id.is_not(None),
        )
        if user_ids:
            query = query.where(Employee.user_id.in_(user_ids))
        result = await self.db.execute(query)
        return {
            employee.user_id: employee
            for employee in result.scalars().all()
            if employee.user_id is not None
        }

    async def _load_all_employees(self) -> list[Employee]:
        result = await self.db.execute(
            select(Employee)
            .where(
                Employee.deleted_at.is_(None),
                Employee.user_id.is_not(None),
            )
            .order_by(Employee.is_active.desc(), Employee.name, Employee.employee_no)
        )
        return list(result.scalars().all())

    async def _load_order_completion_events(
        self,
        *,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> list[BusinessDocumentStatusLog]:
        log = BusinessDocumentStatusLog
        rank = func.row_number().over(
            partition_by=log.document_id,
            order_by=(log.operated_at.desc().nulls_last(), log.id.desc()),
        ).label("event_rank")
        ranked = select(log.id.label("event_id"), rank).subquery()
        conditions = [
            ranked.c.event_rank == 1,
            log.to_status == "completed",
            BusinessDocument.status == "completed",
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        ]
        if period_start is not None:
            conditions.extend((log.operated_at.is_not(None), log.operated_at >= period_start))
        if period_end is not None:
            conditions.append(log.operated_at < period_end)
        result = await self.db.execute(
            select(log)
            .join(ranked, ranked.c.event_id == log.id)
            .join(BusinessDocument, BusinessDocument.id == log.document_id)
            .where(*conditions)
        )
        return list(result.scalars().all())

    async def _prepare_events(self, events: list[CompletionEvent]) -> dict[UUID, Employee]:
        await self._load_task_metadata(events)
        user_ids = {
            event.assignee_user_id
            for event in events
            if event.assignee_user_id is not None
        }
        employees = await self._load_employees(user_ids)
        for event in events:
            employee = employees.get(event.assignee_user_id)
            event.assignee_name = employee.name if employee else None
        return employees

    @staticmethod
    def _project_rows(events: list[CompletionEvent]) -> list[dict]:
        groups: dict[UUID, list[CompletionEvent]] = defaultdict(list)
        for event in events:
            groups[event.document_id].append(event)
        rows = []
        for project_id, project_events in groups.items():
            timestamps = [event.operated_at for event in project_events if event.operated_at]
            rows.append(
                {
                    "kind": "project",
                    "project_id": str(project_id),
                    "project_no": project_events[0].project_no,
                    "project_name": project_events[0].project_name,
                    "completed_detail_count": len({event.order_item_id for event in project_events}),
                    "completed_work_unit_count": len(project_events),
                    "stages": sorted(
                        {event.task_type for event in project_events},
                        key=TASK_TYPES.index,
                    ),
                    "last_completed_at": _iso_datetime(max(timestamps) if timestamps else None),
                }
            )
        return sorted(
            rows,
            key=lambda row: (row["last_completed_at"] is not None, row["last_completed_at"] or ""),
            reverse=True,
        )

    async def get_summary(self, period: str) -> dict:
        period_start, period_end = get_task_completion_period(period)
        scope = await self._resolve_scope(None)
        current_employee = scope["current_employee"]
        base = {
            "period": period,
            "period_start": period_start.date().isoformat() if period_start else None,
            "period_end": period_end.date().isoformat() if period_end else None,
            "scope": scope["scope"],
            "employee": _employee_payload(current_employee),
            "own": _zero_stats(),
            "organization": None,
            "employees": [],
            "unassigned": _zero_stats(),
            "message": None,
        }
        if scope["no_data"]:
            base["message"] = "当前账号未绑定在职员工，暂无法显示个人完成统计"
            return base

        events = await self._load_latest_events(owner_user_id=scope["owner_user_id"])
        events = _select_current_completed_work_units(
            events,
            period_start=period_start,
            period_end=period_end,
        )
        await self._prepare_events(events)

        viewer_id = getattr(self.viewer, "id", None)
        base["own"] = _stats(
            _select_current_completed_work_units(
                events,
                owner_user_id=viewer_id,
            )
        )
        if scope["scope"] != "all":
            return base

        employee_records = await self._load_all_employees()
        employee_map = {employee.user_id: employee for employee in employee_records if employee.user_id}
        grouped: dict[UUID, list[CompletionEvent]] = defaultdict(list)
        unassigned: list[CompletionEvent] = []
        for event in events:
            if event.assignee_user_id is None or event.assignee_user_id not in employee_map:
                unassigned.append(event)
            else:
                grouped[event.assignee_user_id].append(event)

        employee_rows = []
        for employee in employee_records:
            row = _employee_payload(employee)
            row.update(_stats(grouped.get(employee.user_id, [])))
            employee_rows.append(row)

        order_completion_events = await self._load_order_completion_events(
            period_start=period_start,
            period_end=period_end,
        )
        installation_item_ids = {
            event.order_item_id
            for event in events
            if event.task_type == "installation"
        }
        base["organization"] = {
            "completed_order_project_count": len({event.document_id for event in order_completion_events}),
            "completed_detail_count": len(installation_item_ids),
            "completed_work_unit_count": len(events),
            "stage_breakdown": _stats(events)["stage_breakdown"],
            "backfill_work_unit_count": sum(event.source == "backfill" for event in events),
            "unknown_completion_time_count": sum(event.operated_at is None for event in events),
        }
        base["employees"] = employee_rows
        base["unassigned"] = _stats(unassigned)
        return base

    async def get_details(
        self,
        *,
        period: str,
        kind: str,
        employee_id: UUID | None,
        task_type: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        if kind not in {"project", "detail"}:
            raise ValueError("明细类型只能选择项目或明细")
        if task_type and task_type not in TASK_TYPES:
            raise ValueError("任务阶段不正确")
        if page < 1 or page_size < 1 or page_size > 100:
            raise ValueError("分页参数不正确")
        period_start, period_end = get_task_completion_period(period)
        scope = await self._resolve_scope(employee_id)
        if scope["no_data"]:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "scope": scope["scope"],
                "message": "当前账号未绑定在职员工，暂无法显示个人完成统计",
            }

        events = await self._load_latest_events(
            owner_user_id=scope["owner_user_id"],
            task_type=task_type,
        )
        events = [
            event
            for event in _select_current_completed_work_units(
                events,
                period_start=period_start,
                period_end=period_end,
                task_type=task_type,
            )
        ]
        await self._prepare_events(events)

        if kind == "project":
            items = self._project_rows(events)
        else:
            items = [
                serialize_completion_detail(
                    project_id=event.document_id,
                    project_no=event.project_no or "",
                    project_name=event.project_name or "",
                    item_id=event.order_item_id,
                    item_name=event.item_name or "未命名明细",
                    task_type=event.task_type,
                    task_id=event.task_id,
                    task_no=event.task_no,
                    assignee_user_id=event.assignee_user_id,
                    assignee_name=event.assignee_name,
                    completed_at=event.operated_at,
                    source=event.source,
                )
                for event in events
            ]

        total = len(items)
        offset = (page - 1) * page_size
        return {
            "items": items[offset : offset + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "scope": scope["scope"],
            "employee": _employee_payload(scope["target_employee"]),
            "message": None,
        }
