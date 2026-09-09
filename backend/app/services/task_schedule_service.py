"""Pure schedule normalization and derived overdue-state helpers."""

from datetime import datetime, timezone


TERMINAL_STATUSES = frozenset({"confirmed", "completed", "cancelled"})
_SCHEDULE_FIELDS = ("planned_start_at", "planned_end_at")


def _coerce_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return value
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise TypeError("计划时间必须是 ISO 日期时间")
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _comparable_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def validate_schedule_range(
    planned_start_at: datetime | str | None,
    planned_end_at: datetime | str | None,
) -> None:
    start = _coerce_datetime(planned_start_at)
    end = _coerce_datetime(planned_end_at)
    if start and end and _comparable_datetime(end) < _comparable_datetime(start):
        raise ValueError("计划结束时间不能早于计划开始时间")


def normalize_task_schedule_data(
    data: dict,
    *,
    current_start_at: datetime | str | None = None,
    current_end_at: datetime | str | None = None,
) -> dict:
    """Normalize schedule input and validate a full create/update range."""
    normalized = dict(data)
    for field in _SCHEDULE_FIELDS:
        if field in normalized:
            normalized[field] = _coerce_datetime(normalized[field])

    validate_schedule_range(
        normalized.get("planned_start_at", current_start_at),
        normalized.get("planned_end_at", current_end_at),
    )
    return normalized


def is_task_overdue(
    planned_end_at: datetime | str | None,
    status: str,
    *,
    now: datetime | None = None,
) -> bool:
    end = _coerce_datetime(planned_end_at)
    if end is None or status in TERMINAL_STATUSES:
        return False
    current = _comparable_datetime(now or datetime.now())
    return current > _comparable_datetime(end)


def overdue_days(
    planned_end_at: datetime | str | None,
    *,
    now: datetime | None = None,
) -> int:
    end = _coerce_datetime(planned_end_at)
    if end is None:
        return 0
    current = _comparable_datetime(now or datetime.now())
    delta = current - _comparable_datetime(end)
    return max(0, delta.days + (1 if delta.total_seconds() > 0 else 0))


def enrich_task_dict_with_schedule_state(
    task_dict: dict,
    *,
    now: datetime | None = None,
) -> dict:
    """Add real-time overdue fields without changing the persisted status."""
    is_overdue = is_task_overdue(
        task_dict.get("planned_end_at"),
        task_dict.get("status", ""),
        now=now,
    )
    task_dict["is_overdue"] = is_overdue
    task_dict["overdue_days"] = overdue_days(task_dict.get("planned_end_at"), now=now) if is_overdue else 0
    return task_dict
