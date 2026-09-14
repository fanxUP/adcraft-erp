"""统一业务状态机定义测试。"""

import pytest

from app.domain.workflows import (
    ACCEPTANCE_WORKFLOW,
    ORDER_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
    ensure_transition,
)
from app.domain.workflow_registry import WORKFLOW_REGISTRY, get_workflow_definition


def test_order_workflow_completes_after_installation():
    assert allowed_targets(ORDER_WORKFLOW, "in_installation") == (
        "designing",
        "in_production",
        "completed",
        "cancelled",
    )


def test_invalid_transition_raises_consistent_error():
    with pytest.raises(ValueError, match="不允许从 completed 流转到 designing"):
        ensure_transition(ORDER_WORKFLOW, "completed", "designing")


def test_delivery_workflows_are_centralized():
    assert allowed_targets(PRODUCTION_TASK_WORKFLOW, "in_progress") == (
        "completed",
        "rework",
        "pending",
    )
    assert allowed_targets(PRODUCTION_TASK_WORKFLOW, "rework") == (
        "in_progress",
    )
    assert allowed_targets(ACCEPTANCE_WORKFLOW, "pending") == (
        "accepted",
        "rejected",
    )

def test_completed_contract_is_terminal():
    from app.domain.workflows import CONTRACT_WORKFLOW

    assert allowed_targets(CONTRACT_WORKFLOW, "completed") == ()


def test_workflow_registry_exposes_immutable_transition_metadata():
    definition = get_workflow_definition("production_task")

    transition = definition.get_transition("in_progress", "completed")

    assert definition.label == "制作任务流程"
    assert transition is not None
    assert transition.command == "production_task.in_progress.to.completed"
    assert transition.label == "制作中 → 已完成"

    with pytest.raises(TypeError):
        definition.transitions["in_progress"] = ()


def test_workflow_registry_has_no_dangling_transition_targets():
    for definition in WORKFLOW_REGISTRY.all():
        state_codes = set(definition.states)
        for source, targets in definition.transitions.items():
            assert source in state_codes
            assert set(targets) <= state_codes
