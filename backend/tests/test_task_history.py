"""Contract tests for task change history backed by operation logs."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest
from app.models.customer import Customer  # noqa: F401 - register ORM relationship targets
from app.models.user import User  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.services import task_history_service
from app.services.task_history_service import (
    _utc_now,
    normalize_task_type,
    record_task_event,
    task_history_snapshot,
)

TASK_ID = UUID("22222222-2222-2222-2222-222222222222")
USER_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_task_history_timestamp_helper_returns_naive_utc():
    expected = datetime(2026, 9, 9, 8, 0, tzinfo=UTC)

    with patch("app.services.task_history_service.datetime") as clock:
        clock.now.return_value = expected
        actual = _utc_now()

    clock.now.assert_called_once_with(UTC)
    assert actual == expected.replace(tzinfo=None)
    assert actual.tzinfo is None


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


def test_order_changes_only_compare_task_items_and_explicit_price_permissions():
    from app.services.task_history_service import order_execution_changes
    snapshot = {
        "before": {"project_name": "旧项目", "total_amount": 999, "items": [
            {"id": "mine", "item_name": "奖牌", "quantity": "1.00", "unit_price": "20", "file_path": "secret"},
            {"id": "other", "item_name": "无关明细", "quantity": 1}]},
        "after": {"project_name": "新项目", "total_amount": 9999, "items": [
            {"id": "mine", "item_name": "奖牌", "quantity": 1, "unit_price": "30", "file_path": "other-secret"},
            {"id": "other", "item_name": "无关明细", "quantity": 8}]},
    }
    changes = task_history_service.order_execution_changes(snapshot, {"mine"}, can_view_price=False)
    assert [row["field"] for row in changes] == ["project_name"]
    assert "secret" not in str(changes) and "无关明细" not in str(changes)
    priced = order_execution_changes(snapshot, {"mine"}, can_view_price=True)
    assert [row["field"] for row in priced] == ["project_name", "unit_price"]


def test_removed_and_new_item_changes_are_preserved():
    from app.services.task_history_service import order_execution_changes
    snapshot = {"before": {"items": [{"id": "old", "item_name": "旧明细", "quantity": 5}]},
                "after": {"items": [{"id": "new", "item_name": "新明细", "quantity": 6}]}}
    changes = order_execution_changes(snapshot, {"old", "new"}, can_view_price=False)
    scopes = {row["item"]: row for row in changes if row["field"] == "lifecycle_status"}
    assert scopes["旧明细"]["after"] == "已移除"
    assert scopes["新明细"]["after"] == "有效明细"


def test_activity_sql_has_scoped_sources_utc_item_time_and_no_outsource_without_permission():
    from sqlalchemy.dialects import postgresql
    task = make_task(document_id=UUID("33333333-3333-3333-3333-333333333333"), created_at=datetime(2026, 9, 1))
    for can_view in (False, True):
        sources = task_history_service._activity_sources("design", task, can_view_outsource=can_view)
        query = __import__("sqlalchemy").union_all(*sources)
        sql = str(query.compile(dialect=postgresql.dialect()))
        params = query.compile(dialect=postgresql.dialect()).params
        assert "task_item_status_logs.task_id =" in sql
        assert "business_document_versions.document_id =" in sql
        assert "business_document_versions.created_at >=" in sql
        assert "attachments.order_id =" in sql and "attachments.stage =" in sql
        assert "task_item_status_logs.operated_at -" in sql
        assert __import__("datetime").timedelta(hours=8) in params.values()
        assert ("outsource_tasks" in sql) is can_view


@pytest.mark.asyncio
@pytest.mark.parametrize("task_type", ["design", "production", "installation"])
async def test_activity_rejects_missing_exact_stage_permission_before_query(task_type):
    from unittest.mock import AsyncMock
    db = AsyncMock()
    with patch("app.core.permissions.user_has_permission", return_value=False):
        with pytest.raises(PermissionError):
            await task_history_service.list_task_activity(db, task_type, TASK_ID, object())
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_activity_rejects_invisible_task():
    from unittest.mock import AsyncMock
    with patch("app.core.permissions.user_has_permission", return_value=True), patch(
        "app.services.order_task_assignment_service.get_visible_task", AsyncMock(return_value=None)
    ):
        with pytest.raises(ValueError, match="无权查看"):
            await task_history_service.list_task_activity(AsyncMock(), "design", TASK_ID, object())


@pytest.mark.asyncio
async def test_activity_paginates_keys_hydrates_sanitized_events_without_writes():
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    task = make_task(document_id=uuid4(), order_item_id=None, created_at=datetime(2026, 9, 1))
    item_id = uuid4()
    operation_id, status_id, version_id, attachment_id = [uuid4() for _ in range(4)]
    time = datetime(2026, 9, 10, 1)
    keys = [SimpleNamespace(id=id_, kind=kind, occurred_at=time if kind != "item" else None)
            for id_, kind in [(operation_id, "operation"), (status_id, "item"), (version_id, "change"), (attachment_id, "attachment")]]
    operation = SimpleNamespace(id=operation_id, user_id=USER_ID, user_name=None, action="update",
                                before_data={"review_required": True, "review_reason": "尺寸变更", "password": "secret"},
                                after_data={"review_required": False, "action": "acknowledge_order_edit_review", "paid_amount": 100})
    status = SimpleNamespace(id=status_id, operated_by=USER_ID, order_item_id=item_id, from_status="pending", to_status="designing")
    version = SimpleNamespace(id=version_id, created_by=USER_ID, version_no=2,
                              snapshot={"reason": "修改数量", "change_batch_id": "batch", "before": {"items": [{"id": str(item_id), "quantity": 1}]},
                                        "after": {"items": [{"id": str(item_id), "quantity": 2}]}})
    attachment = SimpleNamespace(id=attachment_id, uploaded_by=USER_ID, filename="稿件.pdf", file_path="secret-path")
    db = AsyncMock()
    db.scalar.return_value = 35
    def result(rows):
        value = MagicMock()
        value.all.return_value = rows
        value.scalars.return_value.all.return_value = rows
        return value
    db.execute.side_effect = [result(keys), result([operation]), result([status]), result([version]), result([attachment]),
                              result([item_id]), result([SimpleNamespace(id=item_id, item_name="奖牌")]),
                              result([SimpleNamespace(id=USER_ID, real_name="操作员", username="actor")])]
    with patch("app.core.permissions.user_has_permission", side_effect=lambda user, perm: perm == "design_task:read"), patch(
        "app.services.order_task_assignment_service.get_visible_task", AsyncMock(return_value=task)
    ):
        response = await task_history_service.list_task_activity(db, "design", TASK_ID, object(), page=2, page_size=20)
    assert response["total"] == 35 and response["page"] == 2
    assert response["items"][0]["title"] == "已复核订单变更"
    assert response["items"][1]["occurred_at"] is None
    assert response["items"][2]["changes"][0]["after"] == 2
    assert all(row["actor"] == "操作员" for row in response["items"])
    assert "secret" not in str(response) and "paid_amount" not in str(response)
    params = db.execute.call_args_list[0].args[0].compile().params
    assert 20 in params.values()  # server-side LIMIT and OFFSET
    db.flush.assert_not_awaited()
    db.delete.assert_not_awaited()
