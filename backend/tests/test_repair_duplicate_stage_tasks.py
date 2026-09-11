"""Regression tests for the explicit duplicate stage-task repair utility."""

from datetime import datetime
from uuid import UUID

from scripts.repair_duplicate_stage_tasks import build_merge_plan


DOC_ID = UUID("33333333-3333-3333-3333-333333333333")
TASK_ONE_ID = UUID("44444444-4444-4444-4444-444444444444")
TASK_TWO_ID = UUID("55555555-5555-5555-5555-555555555555")
ITEM_ONE_ID = UUID("66666666-6666-6666-6666-666666666666")
ITEM_TWO_ID = UUID("77777777-7777-7777-7777-777777777777")
EMPLOYEE_ID = UUID("88888888-8888-8888-8888-888888888888")


def _task(task_id: UUID, task_no: str, created_at: datetime) -> dict:
    return {
        "id": task_id,
        "task_no": task_no,
        "document_id": DOC_ID,
        "status": "completed",
        "progress_pct": 100,
        "created_at": created_at,
        "completed_at": created_at,
        "order_item_id": None,
    }


def _link(task_id: UUID, item_id: UUID, completed_at: datetime, assignee_user_id=None) -> dict:
    return {
        "task_id": task_id,
        "order_item_id": item_id,
        "position": 0,
        "assignee_user_id": assignee_user_id,
        "item_status": "completed",
        "item_progress_pct": 100,
        "item_completed_at": completed_at,
    }


def test_merge_plan_keeps_oldest_card_and_deduplicates_item_scope():
    first_time = datetime(2026, 9, 9, 12, 48)
    second_time = datetime(2026, 9, 10, 5, 11)
    plan = build_merge_plan(
        "installation",
        [
            _task(TASK_ONE_ID, "I20260909-0002", first_time),
            _task(TASK_TWO_ID, "I20260910-0001", second_time),
        ],
        [
            _link(TASK_ONE_ID, ITEM_ONE_ID, first_time),
            _link(TASK_TWO_ID, ITEM_ONE_ID, second_time, EMPLOYEE_ID),
            _link(TASK_TWO_ID, ITEM_TWO_ID, second_time, EMPLOYEE_ID),
        ],
    )

    assert plan is not None
    assert plan.canonical["id"] == TASK_ONE_ID
    assert [row["id"] for row in plan.duplicates] == [TASK_TWO_ID]
    assert [row["order_item_id"] for row in plan.merged_links] == [ITEM_ONE_ID, ITEM_TWO_ID]
    assert plan.merged_links[0]["item_completed_at"] == first_time
    assert plan.merged_links[0]["assignee_user_id"] == EMPLOYEE_ID
    assert plan.aggregate_status == "completed"
    assert plan.aggregate_progress == 100
    assert plan.aggregate_completed_at == second_time


def test_merge_plan_does_not_exist_for_a_single_task():
    plan = build_merge_plan(
        "installation",
        [_task(TASK_ONE_ID, "I20260909-0002", datetime(2026, 9, 9, 12, 48))],
        [],
    )

    assert plan is None


def test_merge_plan_prefers_linked_card_and_handles_unassigned_items():
    first_time = datetime(2026, 8, 3, 10, 0)
    second_time = datetime(2026, 9, 9, 10, 0)
    plan = build_merge_plan(
        "installation",
        [
            _task(TASK_ONE_ID, "I20260803-0001", first_time),
            _task(TASK_TWO_ID, "I20260909-0001", second_time),
        ],
        [_link(TASK_TWO_ID, ITEM_TWO_ID, second_time)],
    )

    assert plan is not None
    assert plan.canonical["id"] == TASK_TWO_ID
    assert [row["id"] for row in plan.duplicates] == [TASK_ONE_ID]
    assert [row["order_item_id"] for row in plan.merged_links] == [ITEM_TWO_ID]
    assert plan.merged_links[0]["assignee_user_id"] is None
