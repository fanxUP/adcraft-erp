"""Scan overdue execution tasks and create idempotent in-app notifications."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import and_, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.task_order_item_link import TaskOrderItemLink
from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN
from app.models.user import Permission, User, role_permissions, user_roles
from app.schemas.notification import NotificationResponse
from app.services.notification_service import broadcast_to_user
from app.services.task_schedule_service import TERMINAL_STATUSES, is_task_overdue


logger = logging.getLogger(__name__)

OVERDUE_NOTIFICATION_TYPE = "task_overdue"
OVERDUE_ESCALATION_NOTIFICATION_TYPE = "task_overdue_escalation"
OVERDUE_ESCALATION_AFTER = timedelta(days=1)
SCAN_INTERVAL_SECONDS = 15 * 60

_TASK_SPECS = (
    (DesignTask.__table__, "design", "design_no", "设计", "/design-tasks/"),
    (ProductionTask.__table__, "production", "production_no", "制作", "/production-tasks/"),
    (InstallationTask.__table__, "installation", "installation_no", "安装", "/installation-tasks/"),
)


@dataclass
class OverdueScanResult:
    eligible: int = 0
    created: int = 0
    skipped_duplicate: int = 0
    skipped_unassigned: int = 0
    escalation_eligible: int = 0
    escalation_created: int = 0
    escalation_skipped_duplicate: int = 0
    escalation_skipped_no_manager: int = 0
    failed: int = 0


def _normalize_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _format_deadline(value: datetime | str) -> str:
    value = _normalize_datetime(value)
    return value.strftime("%Y-%m-%d %H:%M")


def _task_spec(task_type: str) -> tuple[object, str, str, str, str]:
    for spec in _TASK_SPECS:
        if spec[1] == task_type:
            return spec
    raise ValueError(f"不支持的任务类型: {task_type}")


def build_overdue_notification(task_type: str, task) -> dict:
    """Build the existing notification payload for one overdue task."""
    _, _, number_attr, label, route_prefix = _task_spec(task_type)
    task_no = getattr(task, number_attr)
    deadline = _format_deadline(task.planned_end_at)
    return {
        "type_": OVERDUE_NOTIFICATION_TYPE,
        "title": f"{label}任务已逾期",
        "content": f"{label}任务 {task_no} 已超过计划结束时间 {deadline}",
        "link": f"{route_prefix}{task.id}",
    }


def build_overdue_escalation_notification(task_type: str, task) -> dict:
    """Build the management escalation payload for one overdue task."""
    _, _, number_attr, label, route_prefix = _task_spec(task_type)
    task_no = getattr(task, number_attr)
    deadline = _format_deadline(task.planned_end_at)
    return {
        "type_": OVERDUE_ESCALATION_NOTIFICATION_TYPE,
        "title": f"{label}任务逾期升级",
        "content": f"逾期升级：{label}任务 {task_no} 已超过计划结束时间 {deadline}，请及时跟进",
        "link": f"{route_prefix}{task.id}",
    }


def should_notify_task(work_unit, *, now: datetime | None = None) -> bool:
    """Return whether one claimed item work unit is overdue.

    The scanner passes a row carrying ``assignee_user_id`` from
    ``task_order_item_links``.  The legacy task-level ``assigned_to`` column
    is intentionally not a fallback here because it could notify the wrong
    employee when one task contains items owned by different employees.
    """
    return bool(
        getattr(work_unit, "assignee_user_id", None)
        and is_task_overdue(work_unit.planned_end_at, work_unit.status, now=now)
    )


def should_escalate_task(work_unit, *, now: datetime | None = None) -> bool:
    """Return whether one claimed item work unit passed the escalation threshold."""
    current = _normalize_datetime(now or datetime.now())
    return bool(
        should_notify_task(work_unit, now=current)
        and current - _normalize_datetime(work_unit.planned_end_at) >= OVERDUE_ESCALATION_AFTER
    )


async def _list_overdue_tasks(
    db: AsyncSession,
    model,
    task_type: str,
    now: datetime,
) -> list:
    """Return one row per overdue, claimed order-item work unit.

    A task may have several active items and several executors, so querying
    only the legacy task owner would silently send a mixed task's reminder to
    the wrong person.  Item-level terminal states are excluded as well: a
    completed item inside an overdue mixed task needs no reminder.
    """
    columns = model.c
    link_columns = TaskOrderItemLink.__table__.c
    statement = (
        select(model, link_columns.assignee_user_id.label("assignee_user_id"))
        .select_from(
            model.join(
                TaskOrderItemLink.__table__,
                and_(
                    link_columns.task_type == task_type,
                    link_columns.task_id == columns.id,
                ),
            )
        )
        .where(
            columns.planned_end_at.is_not(None),
            columns.planned_end_at < now,
            columns.status.not_in(TERMINAL_STATUSES),
            or_(columns.scope_status == "active", columns.scope_status.is_(None)),
            link_columns.assignee_user_id.is_not(None),
            or_(
                link_columns.item_status.is_(None),
                link_columns.item_status.not_in(TERMINAL_STATUSES),
            ),
            or_(link_columns.link_status == "active", link_columns.link_status.is_(None)),
        )
    )
    result = await db.execute(
        statement
    )
    return [SimpleNamespace(**row) for row in result.mappings().all()]


async def _notification_exists(
    db: AsyncSession,
    *,
    user_id,
    notification: dict,
) -> bool:
    table = Notification.__table__
    result = await db.execute(
        select(table.c.id).where(
            table.c.user_id == user_id,
            table.c.type == notification["type_"],
            table.c.link == notification["link"],
            table.c.content == notification["content"],
        )
    )
    return result.scalar_one_or_none() is not None


async def _list_active_admin_ids(db: AsyncSession) -> list:
    """Resolve active management recipients by capability, not role name."""
    user_table = User.__table__
    permission_table = Permission.__table__
    statement = (
        select(user_table.c.id)
        .select_from(
            user_table
            .join(user_roles, user_roles.c.user_id == user_table.c.id)
            .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
            .join(permission_table, permission_table.c.id == role_permissions.c.permission_id)
        )
        .where(
            user_table.c.is_active.is_(True),
            user_table.c.deleted_at.is_(None),
            permission_table.c.code == PERM_SYSTEM_SUPER_ADMIN,
        )
        .distinct()
    )
    return list((await db.scalars(statement)).all())


async def _create_notification(
    db: AsyncSession,
    *,
    user_id,
    notification: dict,
) -> None:
    """Persist and broadcast using Core so the scanner has no ORM registry order dependency."""
    table = Notification.__table__
    notification_id = uuid4()
    created_at = datetime.now()
    await db.execute(
        insert(table).values(
            id=notification_id,
            user_id=user_id,
            type=notification["type_"],
            title=notification["title"],
            content=notification["content"],
            link=notification["link"],
            is_read=False,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    await db.commit()

    response = NotificationResponse(
        id=notification_id,
        user_id=user_id,
        type=notification["type_"],
        title=notification["title"],
        content=notification["content"],
        link=notification["link"],
        is_read=False,
        created_at=created_at,
    )
    await broadcast_to_user(
        user_id,
        {"type": "new_notification", "data": response.model_dump(mode="json")},
    )
    unread_count = await db.scalar(
        select(func.count())
        .select_from(table)
        .where(table.c.user_id == user_id, table.c.is_read.is_(False))
    )
    await broadcast_to_user(
        user_id,
        {"type": "unread_count", "data": {"count": unread_count or 0}},
    )


async def scan_overdue_tasks(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> OverdueScanResult:
    """Create at most one notification per task deadline and recipient."""
    current = now or datetime.now()
    summary = OverdueScanResult()
    active_admin_ids = None

    for table, task_type, _, _, _ in _TASK_SPECS:
        work_units = await _list_overdue_tasks(db, table, task_type, current)
        for work_unit in work_units:
            task = work_unit
            assignee_user_id = getattr(work_unit, "assignee_user_id", None)
            if not assignee_user_id:
                summary.skipped_unassigned += 1
                continue
            if not should_notify_task(work_unit, now=current):
                continue

            summary.eligible += 1
            notification = build_overdue_notification(task_type, task)
            if await _notification_exists(
                db,
                user_id=assignee_user_id,
                notification=notification,
            ):
                summary.skipped_duplicate += 1
            else:
                try:
                    await _create_notification(
                        db,
                        user_id=assignee_user_id,
                        notification=notification,
                    )
                    summary.created += 1
                except Exception:
                    summary.failed += 1
                    await db.rollback()
                    logger.exception(
                        "Failed to create overdue notification for %s task %s",
                        task_type,
                        task.id,
                    )

            if not should_escalate_task(work_unit, now=current):
                continue

            if active_admin_ids is None:
                active_admin_ids = await _list_active_admin_ids(db)
            if not active_admin_ids:
                summary.escalation_skipped_no_manager += 1
                continue

            escalation = build_overdue_escalation_notification(task_type, task)
            for admin_id in active_admin_ids:
                if str(admin_id) == str(assignee_user_id):
                    continue
                summary.escalation_eligible += 1
                if await _notification_exists(
                    db,
                    user_id=admin_id,
                    notification=escalation,
                ):
                    summary.escalation_skipped_duplicate += 1
                    continue

                try:
                    await _create_notification(
                        db,
                        user_id=admin_id,
                        notification=escalation,
                    )
                    summary.created += 1
                    summary.escalation_created += 1
                except Exception:
                    summary.failed += 1
                    await db.rollback()
                    logger.exception(
                        "Failed to create overdue escalation for %s task %s to admin %s",
                        task_type,
                        task.id,
                        admin_id,
                    )

    return summary


async def run_overdue_notification_loop(
    interval_seconds: int = SCAN_INTERVAL_SECONDS,
) -> None:
    """Run the scanner until application shutdown."""
    from app.core.database import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                summary = await scan_overdue_tasks(db)
            logger.info(
                "Overdue task notification scan: eligible=%d created=%d "
                "duplicates=%d unassigned=%d escalation_eligible=%d "
                "escalation_created=%d escalation_duplicates=%d "
                "escalation_without_manager=%d failed=%d",
                summary.eligible,
                summary.created,
                summary.skipped_duplicate,
                summary.skipped_unassigned,
                summary.escalation_eligible,
                summary.escalation_created,
                summary.escalation_skipped_duplicate,
                summary.escalation_skipped_no_manager,
                summary.failed,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Overdue task notification scan failed")

        await asyncio.sleep(interval_seconds)
