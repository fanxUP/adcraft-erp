"""Scan overdue execution tasks and create idempotent in-app notifications."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.schemas.notification import NotificationResponse
from app.services.notification_service import broadcast_to_user
from app.services.task_schedule_service import TERMINAL_STATUSES, is_task_overdue


logger = logging.getLogger(__name__)

OVERDUE_NOTIFICATION_TYPE = "task_overdue"
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
    failed: int = 0


def _format_deadline(value: datetime | str) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
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


def should_notify_task(task, *, now: datetime | None = None) -> bool:
    """Return whether an assigned task is currently overdue and non-terminal."""
    return bool(
        task.assigned_to
        and is_task_overdue(task.planned_end_at, task.status, now=now)
    )


async def _list_overdue_tasks(
    db: AsyncSession,
    model,
    task_type: str,
    now: datetime,
) -> list:
    columns = model.c
    result = await db.execute(
        select(model).where(
            columns.planned_end_at.is_not(None),
            columns.planned_end_at < now,
            columns.status.not_in(TERMINAL_STATUSES),
            columns.assigned_to.is_not(None),
        )
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

    for table, task_type, _, _, _ in _TASK_SPECS:
        tasks = await _list_overdue_tasks(db, table, task_type, current)
        for task in tasks:
            if not task.assigned_to:
                summary.skipped_unassigned += 1
                continue
            if not should_notify_task(task, now=current):
                continue

            summary.eligible += 1
            notification = build_overdue_notification(task_type, task)
            if await _notification_exists(
                db,
                user_id=task.assigned_to,
                notification=notification,
            ):
                summary.skipped_duplicate += 1
                continue

            try:
                await _create_notification(
                    db,
                    user_id=task.assigned_to,
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
                "duplicates=%d unassigned=%d failed=%d",
                summary.eligible,
                summary.created,
                summary.skipped_duplicate,
                summary.skipped_unassigned,
                summary.failed,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Overdue task notification scan failed")

        await asyncio.sleep(interval_seconds)
