"""统一业务状态机定义测试。"""

import pytest

from app.domain.workflows import (
    ACCEPTANCE_WORKFLOW,
    ORDER_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
    ensure_transition,
)


def test_order_workflow_requires_acceptance():
    assert allowed_targets(ORDER_WORKFLOW, "in_installation") == (
        "designing",
        "in_production",
        "pending_acceptance",
        "cancelled",
    )
    assert allowed_targets(ORDER_WORKFLOW, "pending_acceptance") == (
        "completed",
        "in_installation",
        "cancelled",
    )


def test_invalid_transition_raises_consistent_error():
    with pytest.raises(ValueError, match="不允许从 completed 流转到 designing"):
        ensure_transition(ORDER_WORKFLOW, "completed", "designing")


def test_delivery_workflows_are_centralized():
    assert allowed_targets(PRODUCTION_TASK_WORKFLOW, "rework") == (
        "in_progress",
        "cancelled",
    )
    assert allowed_targets(ACCEPTANCE_WORKFLOW, "pending") == (
        "accepted",
        "rejected",
    )

def test_completed_contract_is_terminal():
    from app.domain.workflows import CONTRACT_WORKFLOW

    assert allowed_targets(CONTRACT_WORKFLOW, "completed") == ()
