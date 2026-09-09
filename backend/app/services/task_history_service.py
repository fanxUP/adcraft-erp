"""Task audit history backed by the existing operation_logs table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog
from app.services.operation_log_service import (
    ACTION_CREATE,
    ACTION_STATUS_CHANGE,
    ACTION_UPDATE,
)

TASK_OBJECT_TYPES = {
    "design": "design_task",
    "production": "production_task",
    "installation": "installation_task",
}
TASK_HISTORY_ACTIONS = (ACTION_CREATE, ACTION_UPDATE, ACTION_STATUS_CHANGE)
AUDITABLE_FIELDS = {
    "status",
    "progress_pct",
    "order_item_id",
    "planned_start_at",
    "planned_end_at",
    "assigned_to",
}


def _utc_now() -> datetime:
    """Return naive UTC for the existing operation-log timestamp column."""
    return datetime.now(UTC).replace(tzinfo=None)


async def _append_task_history_log(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    object_type: str,
    object_id: UUID,
    action: str,
    before_data: dict | None,
    after_data: dict,
) -> None:
    await db.execute(
        insert(OperationLog).values(
            user_id=user_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            before_data=before_data,
            after_data=after_data,
            created_at=_utc_now(),
        )
    )


def normalize_task_type(task_type: str) -> str:
    if task_type not in TASK_OBJECT_TYPES:
        raise ValueError(f"不支持的任务类型: {task_type}")
    return TASK_OBJECT_TYPES[task_type]


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def task_history_snapshot(task) -> dict:
    """Return the deliberately small, non-sensitive audit snapshot."""
    snapshot = {
        "status": task.status,
        "progress_pct": task.progress_pct,
        "planned_start_at": _serialize_value(task.planned_start_at),
        "planned_end_at": _serialize_value(task.planned_end_at),
        "assigned_to": _serialize_value(task.assigned_to),
    }
    order_item_id = getattr(task, "order_item_id", None)
    if order_item_id is not None:
        snapshot["order_item_id"] = _serialize_value(order_item_id)
    return snapshot


async def record_task_event(
    db: AsyncSession,
    task_type: str,
    task,
    action: str,
    user_id: UUID | None,
    *,
    before: dict | None = None,
    reason: str | None = None,
    changed_fields: Iterable[str] | None = None,
) -> None:
    """Append an immutable task event to the current transaction."""
    if action not in TASK_HISTORY_ACTIONS:
        raise ValueError(f"不支持的任务历史动作: {action}")

    after = task_history_snapshot(task)
    if reason:
        after["reason"] = reason
    if changed_fields:
        after["changed_fields"] = [
            field for field in changed_fields if field in AUDITABLE_FIELDS
        ]

    await _append_task_history_log(
        db,
        user_id=user_id,
        object_type=normalize_task_type(task_type),
        object_id=task.id,
        action=action,
        before_data=before,
        after_data=after,
    )
