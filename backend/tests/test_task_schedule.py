"""Contract tests for task planned times and derived overdue state."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.task import (
    DesignTaskUpdate,
    InstallationTaskUpdate,
    ProductionTaskUpdate,
    TaskQueueItem,
)
from app.services.task_schedule_service import (
    enrich_task_dict_with_schedule_state,
    is_task_overdue,
    normalize_task_schedule_data,
    overdue_days,
    validate_schedule_range,
)


NOW = datetime(2026, 9, 7, 10, 0, 0)


@pytest.mark.parametrize(
    "schema",
    [DesignTaskUpdate, ProductionTaskUpdate, InstallationTaskUpdate],
)
def test_task_schedule_fields_accept_iso_datetime(schema):
    data = schema(
        planned_start_at="2026-09-07T09:00:00",
        planned_end_at="2026-09-07T18:00:00",
    )

    assert data.planned_start_at == datetime(2026, 9, 7, 9, 0, 0)
    assert data.planned_end_at == datetime(2026, 9, 7, 18, 0, 0)


def test_task_schedule_rejects_end_before_start():
    with pytest.raises(ValidationError):
        DesignTaskUpdate(
            planned_start_at="2026-09-07T18:00:00",
            planned_end_at="2026-09-07T09:00:00",
        )


def test_validate_schedule_range_supports_aware_datetimes():
    start = datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    validate_schedule_range(start, end)

    with pytest.raises(ValueError):
        validate_schedule_range(end, start)


def test_normalize_task_schedule_data_stores_aware_input_as_utc_naive():
    normalized = normalize_task_schedule_data(
        {"planned_end_at": "2026-09-07T18:00:00+08:00"}
    )

    assert normalized["planned_end_at"] == datetime(2026, 9, 7, 10, 0, 0)


@pytest.mark.parametrize(
    ("planned_end_at", "status", "expected"),
    [
        (None, "pending", False),
        (NOW + timedelta(minutes=1), "pending", False),
        (NOW - timedelta(minutes=1), "pending", True),
        (NOW - timedelta(days=2), "confirmed", False),
        (NOW - timedelta(days=2), "completed", False),
        (NOW - timedelta(days=2), "cancelled", False),
    ],
)
def test_is_task_overdue_uses_live_time_and_terminal_statuses(
    planned_end_at, status, expected
):
    assert is_task_overdue(planned_end_at, status, now=NOW) is expected


def test_overdue_days_is_at_least_one_for_same_day_overdue_task():
    assert overdue_days(NOW - timedelta(minutes=1), now=NOW) == 1
    assert overdue_days(NOW + timedelta(minutes=1), now=NOW) == 0


def test_enrichment_adds_derived_overdue_fields_without_mutating_status():
    item = {
        "status": "in_progress",
        "planned_start_at": "2026-09-06T09:00:00",
        "planned_end_at": "2026-09-06T18:00:00",
    }

    enriched = enrich_task_dict_with_schedule_state(item, now=NOW)

    assert enriched["is_overdue"] is True
    assert enriched["overdue_days"] == 1
    assert enriched["status"] == "in_progress"


def test_task_queue_item_exposes_schedule_contract():
    item = TaskQueueItem(
        id="task-id",
        task_type="production",
        stage="production",
        task_no="P20260907-0001",
        document_id="order-id",
        project_name="门头制作",
        status="in_progress",
        progress_pct=65,
        planned_start_at="2026-09-07T09:00:00",
        planned_end_at="2026-09-07T18:00:00",
        is_overdue=True,
        overdue_days=1,
    )

    assert item.planned_end_at == "2026-09-07T18:00:00"
    assert item.is_overdue is True
    assert item.overdue_days == 1


def test_schedule_migration_is_additive_and_reversible():
    migration_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in migration_dir.glob("*.py")
        if "task_schedule_dates" in path.name
    )

    assert 'revision = "n5o6p7q8r9s0"' in source
    assert 'down_revision = "m4n5o6p7q8r9"' in source
    assert '"design_tasks", "production_tasks", "installation_tasks"' in source
    assert source.count('op.add_column(table_name') == 2
    assert '"installation_tasks", "production_tasks", "design_tasks"' in source
    assert source.count('op.drop_column(table_name') == 2
