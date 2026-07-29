import pytest

from app.ai_assistant.business_rules.catalog import build_business_rule_catalog
from app.ai_assistant.page_capabilities import (
    GUIDANCE_BUSINESS_TYPES,
    load_page_capabilities,
    validate_page_action_target,
)


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
    assert capability_rule.payload["version"] == 1
    assert "order-status-confirmed" in capability_rule.payload["target_keys"]
