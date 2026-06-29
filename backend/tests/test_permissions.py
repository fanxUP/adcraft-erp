"""Tests for RBAC permission dependency: require_permission and require_role."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.permissions import require_permission, require_role

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
        role = _make_role("editor", ["document:read", "document:write"])
        user = _make_user([role])
        assert await self._check("document:write", user) is True

    async def test_user_without_permission_fails(self):
        """User without the required permission fails with 403."""
        role = _make_role("viewer", ["document:read"])
        user = _make_user([role])
        assert await self._check("document:write", user) is False

    async def test_user_with_multiple_roles_checks_all(self):
        """The dependency checks all roles, not just the first one."""
        role_a = _make_role("role_a", ["perm:a"])
        role_b = _make_role("role_b", ["perm:b"])
        user = _make_user([role_a, role_b])
        assert await self._check("perm:a", user) is True
        assert await self._check("perm:b", user) is True
        assert await self._check("perm:c", user) is False

    async def test_user_with_no_roles_fails(self):
        """User with no roles fails for any permission."""
        user = _make_user([])
        assert await self._check("anything", user) is False

    async def test_permission_in_any_role_suffices(self):
        """Having the permission in any one role is sufficient."""
        viewer = _make_role("viewer", ["read"])
        editor = _make_role("editor", ["read", "write"])
        user = _make_user([viewer, editor])
        assert await self._check("write", user) is True

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
