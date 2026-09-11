"""Tests for the modular permission catalog and authorization evaluator."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.authorization import AuthorizationEvaluator
from app.core.permission_catalog import (
    get_permission_pack,
    get_permission_dependencies,
    get_permission_definition,
    permission_pack_definitions,
    permission_definitions,
    validate_permission_catalog,
    validate_permission_set,
)
from app.core.permissions import (
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_AI_QUOTE_READ,
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_ORDER_READ,
    PERM_ORDER_VIEW_PRICE,
    PERM_OUTSOURCE_CENTER_READ,
    PERM_OUTSOURCE_TASK_READ,
    PERM_PAYMENT_READ,
    PERM_SYSTEM_SUPER_ADMIN,
)


def _user(*permission_codes: str):
    return SimpleNamespace(
        roles=[
            SimpleNamespace(
                name="arbitrary-role-name",
                permissions=[SimpleNamespace(code=code) for code in permission_codes],
            )
        ]
    )


def test_every_declared_permission_has_structured_catalog_metadata():
    definitions = permission_definitions()

    assert definitions
    assert len({definition.code for definition in definitions}) == len(definitions)
    assert all(definition.module for definition in definitions)
    assert all(definition.resource for definition in definitions)
    assert all(definition.action for definition in definitions)
    assert get_permission_definition(PERM_ORDER_VIEW_PRICE).kind == "field"
    assert get_permission_definition(PERM_ORDER_VIEW_PRICE).sensitivity == "price"


def test_permission_catalog_has_no_unknown_dependencies_or_cycles():
    assert validate_permission_catalog() == ()


def test_builtin_seeded_role_compositions_are_valid():
    from scripts.seed_permissions import ROLE_PERMISSION_MAP

    for role_name, permission_codes in ROLE_PERMISSION_MAP.items():
        assert validate_permission_set(permission_codes) == [], role_name


def test_permission_packs_are_catalogued_and_expand_to_valid_atomic_permissions():
    packs = permission_pack_definitions()

    assert packs
    assert get_permission_pack("design_task_operator").name == "设计任务处理"
    for pack in packs:
        assert validate_permission_set(pack.permissions) == [], pack.code


def test_permission_dependencies_are_transitive_and_explicit():
    assert get_permission_dependencies(PERM_ORDER_VIEW_PRICE) == (PERM_ORDER_READ,)
    assert get_permission_dependencies(PERM_DESIGN_TASK_CHANGE_STATUS) == (
        PERM_DESIGN_TASK_READ,
    )

    issues = validate_permission_set({PERM_ORDER_VIEW_PRICE})

    assert any(issue.kind == "missing_dependency" for issue in issues)
    assert any(PERM_ORDER_READ in issue.permissions for issue in issues)


def test_unrelated_custom_roles_can_be_combined_without_role_name_rules():
    issues = validate_permission_set({PERM_DESIGN_TASK_READ, PERM_OUTSOURCE_TASK_READ, PERM_OUTSOURCE_CENTER_READ})

    assert issues == []


def test_task_mutation_and_price_permissions_are_a_code_level_conflict():
    issues = validate_permission_set(
        {
            PERM_DESIGN_TASK_UPDATE,
            PERM_DESIGN_TASK_READ,
            PERM_ORDER_VIEW_PRICE,
            PERM_ORDER_READ,
        }
    )

    conflict = next(issue for issue in issues if issue.kind == "conflict")
    assert "任务执行" in conflict.message
    assert PERM_ORDER_VIEW_PRICE in conflict.permissions


def test_business_ai_permissions_are_sensitive_for_custom_compositions():
    issues = validate_permission_set({PERM_DESIGN_TASK_UPDATE, PERM_DESIGN_TASK_READ, PERM_AI_QUOTE_READ})

    assert any(issue.kind == "conflict" for issue in issues)


def test_super_admin_permission_is_the_only_conflict_bypass():
    issues = validate_permission_set(
        {
            PERM_SYSTEM_SUPER_ADMIN,
            PERM_DESIGN_TASK_UPDATE,
            PERM_ORDER_VIEW_PRICE,
        }
    )

    assert not [issue for issue in issues if issue.kind == "conflict"]


def test_evaluator_explains_missing_dependency_in_plain_language():
    decision = AuthorizationEvaluator(_user(PERM_ORDER_VIEW_PRICE)).check(PERM_ORDER_VIEW_PRICE)

    assert decision.allowed is False
    assert decision.reason_code == "AUTHZ_DEPENDENCY_MISSING"
    assert PERM_ORDER_READ in decision.missing_permissions
    assert "前置" in decision.message


def test_evaluator_blocks_sensitive_field_when_existing_roles_are_conflicted():
    viewer = _user(PERM_DESIGN_TASK_UPDATE, PERM_DESIGN_TASK_READ, PERM_ORDER_READ, PERM_ORDER_VIEW_PRICE)

    decision = AuthorizationEvaluator(viewer).check(PERM_ORDER_VIEW_PRICE)

    assert decision.allowed is False
    assert decision.reason_code == "AUTHZ_COMBINATION_CONFLICT"
    assert PERM_ORDER_VIEW_PRICE in decision.conflicting_permissions


def test_evaluator_allows_valid_multi_role_union():
    viewer = SimpleNamespace(
        roles=[
            SimpleNamespace(name="one", permissions=[SimpleNamespace(code=PERM_DESIGN_TASK_READ)]),
            SimpleNamespace(name="two", permissions=[SimpleNamespace(code=PERM_ORDER_READ)]),
        ]
    )

    decision = AuthorizationEvaluator(viewer).check_all(PERM_DESIGN_TASK_READ, PERM_ORDER_READ)

    assert decision.allowed is True


@pytest.mark.asyncio
async def test_ai_tool_can_require_multiple_permissions_as_one_contract():
    from app.ai_assistant.permission_guard import PermissionGuard
    from app.ai_assistant.tool_registry import AiToolDefinition

    tool = AiToolDefinition(
        name="receivables",
        description="测试财务查询",
        parameters={"type": "object"},
        required_permissions=(PERM_ORDER_VIEW_PRICE, PERM_PAYMENT_READ),
    )
    guard = PermissionGuard(None)

    sales_without_payment = _user(PERM_ORDER_READ, PERM_ORDER_VIEW_PRICE)
    sales_with_payment = _user(
        PERM_ORDER_READ,
        PERM_ORDER_VIEW_PRICE,
        PERM_PAYMENT_READ,
    )

    assert await guard.check_permission(sales_without_payment, tool) is False
    assert await guard.check_permission(sales_with_payment, tool) is True


def test_ai_order_and_receivable_tools_use_scoped_permission_contracts():
    from app.ai_assistant.tool_registry import ToolRegistry
    from app.ai_assistant.tools.customer_tools import register_customer_tools
    from app.ai_assistant.tools.finance_tools import register_finance_tools
    from app.ai_assistant.tools.order_tools import register_order_tools

    register_order_tools()
    register_customer_tools()
    register_finance_tools()
    registry = ToolRegistry()

    assert registry.get("search_orders").required_permission == PERM_ORDER_READ
    assert registry.get("get_order_detail").required_permission == PERM_ORDER_READ
    assert registry.get("get_order_progress").required_permission == PERM_ORDER_READ
    receivables = registry.get("get_customer_receivables")
    assert receivables.required_permissions == (
        PERM_ORDER_VIEW_PRICE,
        PERM_PAYMENT_READ,
    )


def test_business_routes_do_not_authorize_by_role_name():
    """Keep role labels out of the request boundary as the catalog evolves."""

    app_root = Path(__file__).resolve().parents[1] / "app"
    route_sources = sorted(
        {
            *((app_root / "api").rglob("*.py")),
            *((app_root / "ai").rglob("*.py")),
            app_root / "ai_assistant" / "router.py",
        }
    )
    forbidden_fragments = (
        "require_role(",
        "require_any_role(",
        "role.name",
    )

    violations = [
        f"{path}:{line_number}: {line.strip()}"
        for path in route_sources
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if any(fragment in line for fragment in forbidden_fragments)
    ]

    assert violations == []
