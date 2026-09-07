"""Task audit history backed by the existing operation_logs table."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog
from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.user import User
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
TASK_TYPE_BY_OBJECT = {value: key for key, value in TASK_OBJECT_TYPES.items()}
TASK_HISTORY_ACTIONS = (ACTION_CREATE, ACTION_UPDATE, ACTION_STATUS_CHANGE)
AUDITABLE_FIELDS = {
    "status",
    "progress_pct",
    "order_item_id",
    "planned_start_at",
    "planned_end_at",
    "assigned_to",
}
TASK_MODELS = {
    "design": DesignTask,
    "production": ProductionTask,
    "installation": InstallationTask,
}


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
            created_at=datetime.now(),
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


def build_task_history_item(log: OperationLog, user_name: str | None = None) -> dict:
    before = log.before_data or {}
    after = log.after_data or {}
    task_type = TASK_TYPE_BY_OBJECT.get(log.object_type)

    return {
        "id": str(log.id),
        "task_type": task_type,
        "task_id": str(log.object_id),
        "action": log.action,
        "user_id": str(log.user_id) if log.user_id else None,
        "user_name": user_name or log.user_name,
        "changed_at": log.created_at.isoformat() if log.created_at else None,
        "from_status": before.get("status"),
        "to_status": after.get("status"),
        "from_progress_pct": before.get("progress_pct"),
        "to_progress_pct": after.get("progress_pct"),
        "reason": after.get("reason"),
        "changed_fields": after.get("changed_fields") or [],
    }


async def task_exists(db: AsyncSession, task_type: str, task_id: UUID) -> bool:
    if task_type not in TASK_MODELS:
        raise ValueError(f"不支持的任务类型: {task_type}")
    return await db.get(TASK_MODELS[task_type], task_id) is not None


async def list_task_history(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    object_type = normalize_task_type(task_type)
    base_filter = (
        OperationLog.object_type == object_type,
        OperationLog.object_id == task_id,
        OperationLog.action.in_(TASK_HISTORY_ACTIONS),
    )
    total = (await db.execute(
        select(func.count()).select_from(OperationLog).where(*base_filter)
    )).scalar_one()

    rows = (await db.execute(
        select(OperationLog, User.real_name, User.username)
        .outerjoin(User, User.id == OperationLog.user_id)
        .where(*base_filter)
        .order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all()

    items = []
    for log, real_name, username in rows:
        items.append(build_task_history_item(log, real_name or username))
    return items, total
