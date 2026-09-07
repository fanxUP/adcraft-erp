"""Contract tests for task change history backed by operation logs."""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.schemas.task import TaskHistoryItem
from app.services import task_history_service
from app.services.task_history_service import (
    build_task_history_item,
    normalize_task_type,
    record_task_event,
    task_history_snapshot,
)


TASK_ID = UUID("22222222-2222-2222-2222-222222222222")
USER_ID = UUID("11111111-1111-1111-1111-111111111111")


def make_task(**overrides):
    values = {
        "id": TASK_ID,
        "status": "in_progress",
        "progress_pct": 45,
        "planned_start_at": datetime(2026, 9, 7, 9, 0, 0),
        "planned_end_at": datetime(2026, 9, 7, 18, 0, 0),
        "assigned_to": USER_ID,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_task_history_snapshot_keeps_only_auditable_task_fields():
    snapshot = task_history_snapshot(make_task())

    assert snapshot == {
        "status": "in_progress",
        "progress_pct": 45,
        "planned_start_at": "2026-09-07T09:00:00",
        "planned_end_at": "2026-09-07T18:00:00",
        "assigned_to": str(USER_ID),
    }


def test_normalize_task_type_rejects_unknown_task_types():
    assert normalize_task_type("production") == "production_task"

    with pytest.raises(ValueError, match="不支持的任务类型"):
        normalize_task_type("quote")


@pytest.mark.asyncio
async def test_record_task_event_writes_before_after_snapshots(monkeypatch):
    calls = []

    async def fake_append_log(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(task_history_service, "_append_task_history_log", fake_append_log)

    before = task_history_snapshot(make_task(status="pending", progress_pct=0))
    await record_task_event(
        db=object(),
        task_type="production",
        task=make_task(),
        action="status_change",
        user_id=USER_ID,
        before=before,
        reason="开始制作",
        changed_fields=["status", "progress_pct"],
    )

    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["object_type"] == "production_task"
    assert kwargs["object_id"] == TASK_ID
    assert kwargs["action"] == "status_change"
    assert kwargs["before_data"] == before
    assert kwargs["after_data"]["status"] == "in_progress"
    assert kwargs["after_data"]["reason"] == "开始制作"
    assert kwargs["after_data"]["changed_fields"] == ["status", "progress_pct"]


def test_build_task_history_item_returns_frontend_contract():
    log = SimpleNamespace(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        user_id=USER_ID,
        user_name=None,
        object_type="installation_task",
        object_id=TASK_ID,
        action="update",
        before_data={"status": "assigned", "progress_pct": 20},
        after_data={"status": "assigned", "progress_pct": 40, "changed_fields": ["progress_pct"]},
        created_at=datetime(2026, 9, 7, 10, 0, 0),
    )

    item = TaskHistoryItem.model_validate(build_task_history_item(log, "李四"))

    assert item.task_type == "installation"
    assert item.task_id == str(TASK_ID)
    assert item.action == "update"
    assert item.user_name == "李四"
    assert item.from_status == "assigned"
    assert item.to_status == "assigned"
    assert item.from_progress_pct == 20
    assert item.to_progress_pct == 40
    assert item.changed_fields == ["progress_pct"]
