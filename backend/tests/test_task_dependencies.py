"""Contract tests for same-order task dependencies and derived blocking state."""

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskQueueItem
from app.schemas.task_dependency import TaskDependencyCreate
from app.services.task_dependency_service import (
    dependency_edge_would_cycle,
    dependency_status_is_satisfied,
    progression_statuses_for,
)


def test_dependency_create_accepts_finish_to_start_edge():
    data = TaskDependencyCreate(
        predecessor_task_type="design",
        predecessor_task_id="11111111-1111-1111-1111-111111111111",
        successor_task_type="production",
        successor_task_id="22222222-2222-2222-2222-222222222222",
    )

    assert data.dependency_type == "finish_to_start"
    assert data.successor_task_type == "production"


def test_dependency_create_rejects_unknown_type_or_relation():
    with pytest.raises(ValidationError):
        TaskDependencyCreate(
            predecessor_task_type="quote",
            predecessor_task_id="11111111-1111-1111-1111-111111111111",
            successor_task_type="production",
            successor_task_id="22222222-2222-2222-2222-222222222222",
        )

    with pytest.raises(ValidationError):
        TaskDependencyCreate(
            predecessor_task_type="design",
            predecessor_task_id="11111111-1111-1111-1111-111111111111",
            successor_task_type="production",
            successor_task_id="22222222-2222-2222-2222-222222222222",
            dependency_type="start_to_start",
        )


def test_dependency_cycle_detection_rejects_reverse_edge():
    edges = {
        (("design", "a"), ("production", "b")),
        (("production", "b"), ("installation", "c")),
    }

    assert dependency_edge_would_cycle(
        edges,
        ("installation", "c"),
        ("design", "a"),
    )
    assert not dependency_edge_would_cycle(
        edges,
        ("design", "a"),
        ("installation", "c"),
    )


@pytest.mark.parametrize(
    ("task_type", "status", "expected"),
    [
        ("design", "confirmed", True),
        ("design", "completed", True),
        ("design", "designing", False),
        ("production", "completed", True),
        ("installation", "completed", True),
        ("installation", "cancelled", False),
    ],
)
def test_dependency_status_is_satisfied(task_type, status, expected):
    assert dependency_status_is_satisfied(task_type, status) is expected


def test_progression_statuses_are_limited_to_work_and_completion():
    assert "in_progress" in progression_statuses_for("production")
    assert "completed" in progression_statuses_for("installation")
    assert "cancelled" not in progression_statuses_for("installation")


def test_queue_item_exposes_blocking_contract():
    item = TaskQueueItem(
        id="task-id",
        task_type="production",
        stage="production",
        task_no="P20260907-0001",
        document_id="order-id",
        project_name="门头制作",
        status="pending",
        progress_pct=0,
        is_blocked=True,
        blocked_reason="前置任务 D20260907-0001 尚未完成",
        blocking_tasks=[
            {
                "task_type": "design",
                "task_id": "design-id",
                "task_no": "D20260907-0001",
                "project_name": "门头设计",
                "status": "designing",
                "progress_pct": 60,
            }
        ],
    )

    assert item.is_blocked is True
    assert item.blocking_tasks[0].task_no == "D20260907-0001"
