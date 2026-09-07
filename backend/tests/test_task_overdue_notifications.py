"""Contract tests for automatic overdue task notifications."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services import task_overdue_notification_service as overdue_service


NOW = datetime(2026, 9, 7, 10, 0, 0)
USER_ID = UUID("11111111-1111-1111-1111-111111111111")
ADMIN_ID = UUID("33333333-3333-3333-3333-333333333333")
TASK_ID = UUID("22222222-2222-2222-2222-222222222222")


def make_task(task_type="design", **overrides):
    no_field = {
        "design": "design_no",
        "production": "production_no",
        "installation": "installation_no",
    }[task_type]
    values = {
        "id": TASK_ID,
        no_field: f"{task_type[:1].upper()}20260907-0001",
        "project_name": "门头项目",
        "status": "in_progress",
        "planned_end_at": NOW - timedelta(minutes=30),
        "assigned_to": USER_ID,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_overdue_notification_contains_task_link_and_deadline():
    payload = overdue_service.build_overdue_notification("design", make_task())

    assert payload == {
        "type_": "task_overdue",
        "title": "设计任务已逾期",
        "content": "设计任务 D20260907-0001 已超过计划结束时间 2026-09-07 09:30",
        "link": f"/design-tasks/{TASK_ID}",
    }


def test_build_overdue_escalation_notification_is_distinct_and_actionable():
    payload = overdue_service.build_overdue_escalation_notification("design", make_task())

    assert payload == {
        "type_": "task_overdue_escalation",
        "title": "设计任务逾期升级",
        "content": "逾期升级：设计任务 D20260907-0001 已超过计划结束时间 2026-09-07 09:30，请及时跟进",
        "link": f"/design-tasks/{TASK_ID}",
    }


@pytest.mark.parametrize(
    ("status", "assigned_to", "planned_end_at", "expected"),
    [
        ("in_progress", USER_ID, NOW - timedelta(minutes=30), True),
        ("confirmed", USER_ID, NOW - timedelta(minutes=30), False),
        ("completed", USER_ID, NOW - timedelta(minutes=30), False),
        ("cancelled", USER_ID, NOW - timedelta(minutes=30), False),
        ("in_progress", None, NOW - timedelta(minutes=30), False),
        ("in_progress", USER_ID, NOW + timedelta(minutes=30), False),
    ],
)
def test_should_notify_only_non_terminal_assigned_overdue_tasks(
    status, assigned_to, planned_end_at, expected
):
    task = make_task(
        status=status,
        assigned_to=assigned_to,
        planned_end_at=planned_end_at,
    )

    assert overdue_service.should_notify_task(task, now=NOW) is expected


@pytest.mark.parametrize(
    ("status", "assigned_to", "planned_end_at", "expected"),
    [
        ("in_progress", USER_ID, NOW - timedelta(days=1), True),
        ("in_progress", USER_ID, NOW - timedelta(days=1, minutes=-1), False),
        ("confirmed", USER_ID, NOW - timedelta(days=2), False),
        ("completed", USER_ID, NOW - timedelta(days=2), False),
        ("cancelled", USER_ID, NOW - timedelta(days=2), False),
        ("in_progress", None, NOW - timedelta(days=2), False),
    ],
)
def test_should_escalate_only_after_one_day_and_only_for_assigned_non_terminal_tasks(
    status, assigned_to, planned_end_at, expected
):
    task = make_task(
        status=status,
        assigned_to=assigned_to,
        planned_end_at=planned_end_at,
    )

    assert overdue_service.should_escalate_task(task, now=NOW) is expected


@pytest.mark.asyncio
async def test_scan_is_idempotent_and_re_sends_after_deadline_changes(monkeypatch):
    task = make_task()
    sent = []
    existing = set()

    async def fake_list_overdue_tasks(db, model, task_type, now):
        return [task] if task_type == "design" else []

    async def fake_notification_exists(db, *, user_id, notification):
        key = (
            user_id,
            notification["type_"],
            notification["link"],
            notification["content"],
        )
        return key in existing

    async def fake_create_notification(db, *, user_id, notification):
        kwargs = {"user_id": user_id, **notification}
        sent.append(kwargs)
        existing.add(
            (
                kwargs["user_id"],
                kwargs["type_"],
                kwargs["link"],
                kwargs["content"],
            )
        )

    monkeypatch.setattr(overdue_service, "_list_overdue_tasks", fake_list_overdue_tasks)
    monkeypatch.setattr(overdue_service, "_notification_exists", fake_notification_exists)
    monkeypatch.setattr(overdue_service, "_create_notification", fake_create_notification)

    first = await overdue_service.scan_overdue_tasks(object(), now=NOW)
    second = await overdue_service.scan_overdue_tasks(object(), now=NOW)

    assert first.created == 1
    assert second.created == 0
    assert second.skipped_duplicate == 1
    assert len(sent) == 1

    task.planned_end_at = NOW - timedelta(hours=2)
    third = await overdue_service.scan_overdue_tasks(object(), now=NOW)

    assert third.created == 1
    assert len(sent) == 2
    assert sent[-1]["content"].endswith("08:00")


@pytest.mark.asyncio
async def test_scan_skips_unassigned_task_even_if_query_returns_it(monkeypatch):
    task = make_task(assigned_to=None)
    created = []

    async def fake_list_overdue_tasks(db, model, task_type, now):
        return [task] if task_type == "installation" else []

    async def fake_create_notification(db, *, user_id, notification):
        created.append({"user_id": user_id, **notification})

    monkeypatch.setattr(overdue_service, "_list_overdue_tasks", fake_list_overdue_tasks)
    monkeypatch.setattr(overdue_service, "_create_notification", fake_create_notification)

    result = await overdue_service.scan_overdue_tasks(object(), now=NOW)

    assert result.created == 0
    assert result.skipped_unassigned == 1
    assert created == []


@pytest.mark.asyncio
async def test_scan_escalates_once_to_active_admins_but_not_to_assignee(monkeypatch):
    task = make_task(planned_end_at=NOW - timedelta(days=2))
    sent = []
    existing = set()

    async def fake_list_overdue_tasks(db, model, task_type, now):
        return [task] if task_type == "design" else []

    async def fake_list_active_admin_ids(db):
        return [ADMIN_ID, USER_ID]

    async def fake_notification_exists(db, *, user_id, notification):
        key = (
            user_id,
            notification["type_"],
            notification["link"],
            notification["content"],
        )
        return key in existing

    async def fake_create_notification(db, *, user_id, notification):
        sent.append({"user_id": user_id, **notification})
        existing.add(
            (
                user_id,
                notification["type_"],
                notification["link"],
                notification["content"],
            )
        )

    monkeypatch.setattr(overdue_service, "_list_overdue_tasks", fake_list_overdue_tasks)
    monkeypatch.setattr(overdue_service, "_list_active_admin_ids", fake_list_active_admin_ids)
    monkeypatch.setattr(overdue_service, "_notification_exists", fake_notification_exists)
    monkeypatch.setattr(overdue_service, "_create_notification", fake_create_notification)

    first = await overdue_service.scan_overdue_tasks(object(), now=NOW)
    second = await overdue_service.scan_overdue_tasks(object(), now=NOW)

    assert first.created == 2
    assert first.escalation_created == 1
    assert [item["user_id"] for item in sent] == [USER_ID, ADMIN_ID]
    assert second.created == 0
    assert second.skipped_duplicate == 1
    assert second.escalation_skipped_duplicate == 1


@pytest.mark.asyncio
async def test_scan_does_not_escalate_without_active_admin(monkeypatch):
    task = make_task("production", planned_end_at=NOW - timedelta(days=2))

    async def fake_list_overdue_tasks(db, model, task_type, now):
        return [task] if task_type == "production" else []

    async def fake_list_active_admin_ids(db):
        return []

    async def fake_notification_exists(db, *, user_id, notification):
        return False

    created = []

    async def fake_create_notification(db, *, user_id, notification):
        created.append((user_id, notification))

    monkeypatch.setattr(overdue_service, "_list_overdue_tasks", fake_list_overdue_tasks)
    monkeypatch.setattr(overdue_service, "_list_active_admin_ids", fake_list_active_admin_ids)
    monkeypatch.setattr(overdue_service, "_notification_exists", fake_notification_exists)
    monkeypatch.setattr(overdue_service, "_create_notification", fake_create_notification)

    result = await overdue_service.scan_overdue_tasks(object(), now=NOW)

    assert result.created == 1
    assert result.escalation_created == 0
    assert result.escalation_skipped_no_manager == 1
    assert [item[0] for item in created] == [USER_ID]
