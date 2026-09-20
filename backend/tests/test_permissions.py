"""Tests for RBAC permission dependency: require_permission and require_role."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.permissions import (
    PERM_CATALOG_VIEW_PRICE,
    PERM_CUSTOMER_READ,
    PERM_FINANCE_VIEW_COST,
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_ORDER_CHANGE_DATE,
    PERM_ORDER_VIEW_PRICE,
    PERM_REPORT_VIEW_FINANCIAL,
    PERM_PRODUCT_READ,
    PERM_PROCESS_READ,
    PERM_BACKUP_CREATE,
    PERM_BACKUP_READ,
    PERM_TASK_QUEUE_READ,
    PERM_RESOURCE_CENTER_READ,
    PERM_OUTSOURCE_CENTER_READ,
    PERM_OUTSOURCE_PAYMENT_READ,
    PERM_OUTSOURCE_TASK_CHANGE_STATUS,
    PERM_OUTSOURCE_TASK_CREATE,
    PERM_OUTSOURCE_TASK_DELETE,
    PERM_OUTSOURCE_TASK_READ,
    PERM_OUTSOURCE_TASK_UPDATE,
    PERM_OUTSOURCE_VENDOR_CREATE,
    PERM_OUTSOURCE_VENDOR_DELETE,
    PERM_OUTSOURCE_VENDOR_READ,
    PERM_OUTSOURCE_VENDOR_UPDATE,
    RESOURCE_CENTER_PERMISSION_CODES,
    SENSITIVE_PERMISSION_CODES,
    get_user_capabilities,
    get_user_permission_codes,
    validate_execution_role_combination,
    validate_role_resource_permissions,
    validate_role_sensitive_permissions,
    require_any_permission,
    require_all_permissions,
    require_permission,
    require_role,
)

pytestmark = pytest.mark.asyncio


def _make_role(name: str, permission_codes: list[str]) -> MagicMock:
    """Create a mock Role with the given name and permission codes."""
    role = MagicMock()
    role.name = name
    role.permissions = [_make_perm(code) for code in permission_codes]
    return role


def _make_perm(code: str) -> MagicMock:
    """Create a mock Permission with the given code."""
    perm = MagicMock()
    perm.code = code
    return perm


def _make_user(roles: list[MagicMock]) -> MagicMock:
    """Create a mock User with the given roles."""
    user = MagicMock()
    user.roles = roles
    return user


class TestRequirePermission:
    async def _check(self, permission_code: str, user) -> bool:
        """Helper: call the dependency and return True if it passes."""
        dep = require_permission(permission_code)
        try:
            result = await dep(user)
            assert result is user  # should return the user on success
            return True
        except HTTPException as e:
            assert e.status_code == 403
            return False

    async def test_user_with_permission_passes(self):
        """User with the required permission in one of their roles passes."""
        role = _make_role("editor", [PERM_BACKUP_READ, PERM_BACKUP_CREATE])
        user = _make_user([role])
        assert await self._check(PERM_BACKUP_CREATE, user) is True

    async def test_user_without_permission_fails(self):
        """User without the required permission fails with 403."""
        role = _make_role("viewer", [PERM_BACKUP_READ])
        user = _make_user([role])
        assert await self._check(PERM_BACKUP_CREATE, user) is False

    async def test_user_with_multiple_roles_checks_all(self):
        """The dependency checks all roles, not just the first one."""
        role_a = _make_role("role_a", [PERM_CUSTOMER_READ])
        role_b = _make_role("role_b", [PERM_PRODUCT_READ])
        user = _make_user([role_a, role_b])
        assert await self._check(PERM_CUSTOMER_READ, user) is True
        assert await self._check(PERM_PRODUCT_READ, user) is True
        assert await self._check(PERM_PROCESS_READ, user) is False

    async def test_user_with_no_roles_fails(self):
        """User with no roles fails for any permission."""
        user = _make_user([])
        assert await self._check("anything", user) is False

    async def test_permission_in_any_role_suffices(self):
        """Having the permission in any one role is sufficient."""
        viewer = _make_role("viewer", [PERM_CUSTOMER_READ])
        editor = _make_role("editor", [PERM_CUSTOMER_READ, PERM_PRODUCT_READ])
        user = _make_user([viewer, editor])
        assert await self._check(PERM_PRODUCT_READ, user) is True

    async def test_admin_role_has_all_permissions(self):
        """Admin role (with all permissions) passes any permission check."""
        admin = _make_role("admin", [
            "backup:create", "backup:read",
            "user:create", "user:delete",
            "customer:read",
        ])
        user = _make_user([admin])
        assert await self._check("backup:create", user) is True
        assert await self._check("user:delete", user) is True
        assert await self._check("customer:read", user) is True


class TestRequireAnyPermission:
    async def test_one_matching_permission_is_enough(self):
        user = _make_user([_make_role("operator", [PERM_TASK_QUEUE_READ])])
        dependency = require_any_permission(PERM_BACKUP_CREATE, PERM_TASK_QUEUE_READ)

        assert await dependency(user) is user

    async def test_missing_all_permissions_is_rejected(self):
        user = _make_user([_make_role("viewer", [PERM_CUSTOMER_READ])])
        dependency = require_any_permission(PERM_BACKUP_CREATE, PERM_TASK_QUEUE_READ)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(user)

        assert exc_info.value.status_code == 403


class TestRequireAllPermissions:
    async def test_all_permissions_are_required(self):
        user = _make_user([_make_role("operator", [PERM_CUSTOMER_READ, PERM_PRODUCT_READ])])
        dependency = require_all_permissions(PERM_CUSTOMER_READ, PERM_PRODUCT_READ)

        assert await dependency(user) is user

    async def test_missing_one_permission_is_rejected_with_plain_language(self):
        user = _make_user([_make_role("operator", [PERM_CUSTOMER_READ])])
        dependency = require_all_permissions(PERM_CUSTOMER_READ, PERM_PRODUCT_READ)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(user)

        assert exc_info.value.status_code == 403
        assert PERM_PRODUCT_READ in exc_info.value.detail


async def test_sales_role_can_read_project_delivery_tasks():
    from scripts.seed_permissions import ROLE_PERMISSION_MAP

    sales_permissions = ROLE_PERMISSION_MAP["sales"]
    assert "design_task:read" in sales_permissions
    assert "production_task:read" in sales_permissions
    assert "installation_task:read" in sales_permissions


async def test_every_declared_permission_can_be_seeded():
    from app.core import permissions
    from scripts.seed_permissions import ALL_PERMISSIONS

    declared = {
        value
        for name, value in vars(permissions).items()
        if name.startswith("PERM_") and isinstance(value, str)
    }
    seeded = {permission["code"] for permission in ALL_PERMISSIONS}

    assert declared <= seeded


async def test_role_mappings_only_reference_seeded_permissions():
    from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP

    seeded = {permission["code"] for permission in ALL_PERMISSIONS}
    mapped = {
        permission
        for permissions in ROLE_PERMISSION_MAP.values()
        for permission in permissions
    }

    assert mapped <= seeded


async def test_order_business_date_permission_requires_order_read_and_is_seeded_for_sales():
    from app.core.permission_catalog import get_permission_dependencies
    from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP

    seeded = {permission["code"] for permission in ALL_PERMISSIONS}
    assert PERM_ORDER_CHANGE_DATE in seeded
    assert PERM_ORDER_CHANGE_DATE in ROLE_PERMISSION_MAP["admin"]
    assert PERM_ORDER_CHANGE_DATE in ROLE_PERMISSION_MAP["sales"]
    assert get_permission_dependencies(PERM_ORDER_CHANGE_DATE) == ("order:read",)


async def test_resource_center_parent_permission_is_explicit_and_execution_roles_are_isolated():
    from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP

    seeded = {permission["code"] for permission in ALL_PERMISSIONS}
    assert PERM_RESOURCE_CENTER_READ in seeded

    for role_name in ("admin", "sales", "finance"):
        assert PERM_RESOURCE_CENTER_READ in ROLE_PERMISSION_MAP[role_name]

    for role_name in ("designer", "production", "installer"):
        assert not RESOURCE_CENTER_PERMISSION_CODES.intersection(ROLE_PERMISSION_MAP[role_name])


async def test_outsource_permissions_are_split_and_execution_roles_do_not_get_external_visibility():
    from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP, ROLE_NAMES

    seeded = {permission["code"] for permission in ALL_PERMISSIONS}
    expected = {
        PERM_OUTSOURCE_CENTER_READ,
        PERM_OUTSOURCE_VENDOR_READ,
        PERM_OUTSOURCE_VENDOR_CREATE,
        PERM_OUTSOURCE_VENDOR_UPDATE,
        PERM_OUTSOURCE_VENDOR_DELETE,
        PERM_OUTSOURCE_TASK_READ,
        PERM_OUTSOURCE_TASK_CREATE,
        PERM_OUTSOURCE_TASK_UPDATE,
        PERM_OUTSOURCE_TASK_CHANGE_STATUS,
        PERM_OUTSOURCE_TASK_DELETE,
    }
    assert expected <= seeded
    assert "outsource_manager" in ROLE_NAMES
    assert expected <= set(ROLE_PERMISSION_MAP["outsource_manager"])
    assert PERM_OUTSOURCE_PAYMENT_READ not in ROLE_PERMISSION_MAP["outsource_manager"]

    for role_name in ("designer", "production", "installer"):
        assert not expected.intersection(ROLE_PERMISSION_MAP[role_name])

    finance_permissions = set(ROLE_PERMISSION_MAP["finance"])
    assert {PERM_OUTSOURCE_CENTER_READ, PERM_OUTSOURCE_VENDOR_READ, PERM_OUTSOURCE_TASK_READ} <= finance_permissions
    assert PERM_OUTSOURCE_TASK_CREATE not in finance_permissions
    assert PERM_OUTSOURCE_TASK_UPDATE not in finance_permissions
    assert PERM_OUTSOURCE_TASK_CHANGE_STATUS not in finance_permissions
    assert PERM_OUTSOURCE_TASK_DELETE not in finance_permissions


async def test_role_permission_refresh_replaces_the_complete_collection():
    from scripts.seed_permissions import replace_role_permissions

    role = MagicMock()
    role.permissions = [_make_perm("stale")]
    target = [_make_perm("order:read"), _make_perm("payment:read")]

    replace_role_permissions(role, target)

    assert [permission.code for permission in role.permissions] == [
        "order:read",
        "payment:read",
    ]


async def test_sensitive_price_permissions_are_seeded_and_mapped_only_to_privileged_roles():
    from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP

    seeded = {permission["code"] for permission in ALL_PERMISSIONS}
    assert SENSITIVE_PERMISSION_CODES <= seeded
    assert SENSITIVE_PERMISSION_CODES <= set(ROLE_PERMISSION_MAP["admin"])
    assert SENSITIVE_PERMISSION_CODES.isdisjoint(set(ROLE_PERMISSION_MAP["designer"]))
    assert SENSITIVE_PERMISSION_CODES.isdisjoint(set(ROLE_PERMISSION_MAP["production"]))
    assert SENSITIVE_PERMISSION_CODES.isdisjoint(set(ROLE_PERMISSION_MAP["installer"]))


async def test_execution_roles_only_read_catalog_metadata():
    from scripts.seed_permissions import ROLE_PERMISSION_MAP

    for role_name in ("designer", "production"):
        role_permissions = set(ROLE_PERMISSION_MAP[role_name])
        assert "product:create" not in role_permissions
        assert "product:update" not in role_permissions
        assert "product:delete" not in role_permissions
        assert "material:create" not in role_permissions
        assert "material:update" not in role_permissions
        assert "material:delete" not in role_permissions
        assert "process:create" not in role_permissions
        assert "process:update" not in role_permissions
        assert "process:delete" not in role_permissions


async def test_permission_context_exposes_price_capabilities_without_role_name_checks():
    user = _make_user([
        _make_role("custom-business", ["order:read", PERM_ORDER_VIEW_PRICE, PERM_REPORT_VIEW_FINANCIAL]),
    ])

    assert get_user_permission_codes(user) == frozenset({
        "order:read",
        PERM_ORDER_VIEW_PRICE,
        PERM_REPORT_VIEW_FINANCIAL,
    })
    assert get_user_capabilities(user) == {
        "view_order_price": True,
        "view_order_item_price": False,
        "view_catalog_price": False,
        "view_cost": False,
        "view_financial_report": True,
    }


async def test_execution_roles_cannot_receive_sensitive_permissions():
    with pytest.raises(ValueError, match="任务执行能力不能与价格或财务能力同时启用"):
        validate_role_sensitive_permissions(
            "designer",
            ["design_task:read", "design_task:update", "order:read", PERM_ORDER_VIEW_PRICE],
        )


async def test_execution_roles_cannot_receive_resource_center_permissions():
    with pytest.raises(ValueError, match="任务执行能力不能与资源中心车辆/高空车能力同时启用"):
        validate_role_resource_permissions(
            "production",
            [
                "production_task:read", "production_task:update",
                PERM_RESOURCE_CENTER_READ, "vehicle:read",
            ],
        )


async def test_custom_execution_role_cannot_hide_sensitive_permissions_behind_a_new_name():
    with pytest.raises(ValueError, match="任务执行能力不能与价格或财务能力同时启用"):
        validate_role_sensitive_permissions(
            "custom-production-team",
            ["production_task:read", "production_task:update", "quote:read"],
        )


async def test_execution_role_cannot_be_combined_with_sales_or_finance():
    # Role names are labels.  Security validation is performed on the
    # effective permission union, so arbitrary role labels do not block a
    # combination by themselves.
    validate_execution_role_combination(["designer", "sales"])
    validate_execution_role_combination(["installer", "finance"])


async def test_admin_can_be_combined_without_triggering_execution_role_conflict():
    validate_execution_role_combination(["admin", "designer", "finance"])


class TestRequireRole:
    async def _check(self, role_name: str, user) -> bool:
        dep = require_role(role_name)
        try:
            result = await dep(user)
            assert result is user
            return True
        except HTTPException as e:
            assert e.status_code == 403
            return False

    async def test_user_with_role_passes(self):
        """User with the matching role passes."""
        role = _make_role("admin", [])
        user = _make_user([role])
        assert await self._check("admin", user) is True

    async def test_user_without_role_fails(self):
        """User without the matching role fails with 403."""
        role = _make_role("sales", [])
        user = _make_user([role])
        assert await self._check("admin", user) is False

    async def test_user_with_multiple_roles(self):
        """User with multiple roles is checked against all."""
        role_a = _make_role("role_a", [])
        role_b = _make_role("role_b", [])
        user = _make_user([role_a, role_b])
        assert await self._check("role_a", user) is True
        assert await self._check("role_b", user) is True

    async def test_user_with_no_roles_fails(self):
        """User with no roles fails any role check."""
        user = _make_user([])
        assert await self._check("admin", user) is False
