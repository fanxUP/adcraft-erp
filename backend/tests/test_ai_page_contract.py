import pytest

from app.ai_assistant.business_rules.catalog import build_business_rule_catalog
from app.ai_assistant.page_capabilities import (
    GUIDANCE_BUSINESS_TYPES,
    build_page_action_semantics,
    load_page_capabilities,
    page_capability_health,
    validate_page_action_target,
)
from app.ai_assistant.workflow_guidance.common import action


def test_page_capability_contract_has_unique_target_keys():
    capabilities = load_page_capabilities()

    target_keys = [capability.target_key for capability in capabilities]

    assert len(target_keys) == len(set(target_keys))
    assert "order-status-confirmed" in target_keys
    assert "installation-draft" in target_keys


def test_page_capability_contract_validates_target_path():
    validate_page_action_target(
        "order-status-confirmed",
        "/orders/11111111-1111-1111-1111-111111111111",
    )
    validate_page_action_target(
        "receivable-register-payment",
        "/receivables?order_id=11111111-1111-1111-1111-111111111111",
    )

    with pytest.raises(ValueError, match="未登记"):
        validate_page_action_target("removed-control", "/orders/1")

    with pytest.raises(ValueError, match="不匹配"):
        validate_page_action_target("order-status-confirmed", "/quotes/1/edit")


def test_every_guidance_business_type_has_a_published_workflow_rule():
    workflow_business_types = {
        rule.payload["business_type"]
        for rule in build_business_rule_catalog()
        if rule.rule_type == "workflow"
    }

    assert GUIDANCE_BUSINESS_TYPES <= workflow_business_types


def test_page_capability_contract_is_part_of_ai_rule_versioning():
    rules = {rule.key: rule for rule in build_business_rule_catalog()}

    capability_rule = rules["contract.page_capabilities"]

    assert capability_rule.rule_type == "capability_contract"
    assert capability_rule.payload["version"] == 2
    assert "order-status-confirmed" in capability_rule.payload["target_keys"]


def test_every_page_capability_declares_safe_operation_semantics():
    capabilities = load_page_capabilities()

    assert capabilities
    for capability in capabilities:
        assert capability.purpose
        assert capability.prerequisites
        assert capability.completion_signal
        assert capability.blocking_conditions
        assert capability.effect in {"read", "write"}
        if capability.effect == "write":
            assert capability.requires_confirmation is True
        for route in capability.routes:
            assert route.required_permission


def test_page_action_semantics_resolve_permission_by_matching_route():
    order_semantics = build_page_action_semantics(
        "task-assignee",
        "/design-tasks/11111111-1111-1111-1111-111111111111",
    )
    installation_semantics = build_page_action_semantics(
        "task-assignee",
        "/installation-tasks/11111111-1111-1111-1111-111111111111",
    )

    assert order_semantics["required_permission"] == "design_task:update"
    assert installation_semantics["required_permission"] == "installation_task:update"
    assert order_semantics["effect"] == "write"
    assert order_semantics["requires_confirmation"] is True


def test_workflow_action_carries_registered_semantics():
    result = action(
        "核对并确认订单",
        "订单详情",
        "/orders/11111111-1111-1111-1111-111111111111",
        target_status="confirmed",
        target_key="order-status-confirmed",
    )

    assert result["semantics"]["purpose"] == "确认订单进入正式交付流程"
    assert result["semantics"]["required_permission"] == "order:change_status"
    assert result["semantics"]["completion_signal"] == "订单状态显示为“已确认”"


def test_page_capability_health_reports_semantic_coverage():
    health = page_capability_health()

    assert health["version"] == 2
    assert health["page_count"] == 7
    assert health["capability_count"] == 32
    assert health["semantic_complete_count"] == 32
    assert health["write_capability_count"] == 31
    assert health["all_write_actions_require_confirmation"] is True
    assert health["unknown_permissions"] == []
