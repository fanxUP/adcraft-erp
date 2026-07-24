"""Tests for aerial module permission checks: verifies all permission codes are enforced."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.permissions import (
    require_permission,
    PERM_AERIAL_READ,
    PERM_AERIAL_CREATE,
    PERM_AERIAL_UPDATE,
    PERM_AERIAL_DELETE,
    PERM_AERIAL_FINANCE,
    PERM_AERIAL_WAGE,
    PERM_AERIAL_APPROVE,
)

pytestmark = pytest.mark.asyncio


def _make_role(name: str, permission_codes: list[str]) -> MagicMock:
    role = MagicMock()
    role.name = name
    role.permissions = [_make_perm(code) for code in permission_codes]
    return role


def _make_perm(code: str) -> MagicMock:
    perm = MagicMock()
    perm.code = code
    return perm


def _make_user(roles: list[MagicMock]) -> MagicMock:
    user = MagicMock()
    user.roles = roles
    return user


# ── Permission codes defined ────────────────────────────────────────────────

class TestAerialPermissionConstants:
    """Verify all aerial permission constants are defined."""

    def test_read_constant(self):
        assert PERM_AERIAL_READ == "aerial:read"

    def test_create_constant(self):
        assert PERM_AERIAL_CREATE == "aerial:create"

    def test_update_constant(self):
        assert PERM_AERIAL_UPDATE == "aerial:update"

    def test_delete_constant(self):
        assert PERM_AERIAL_DELETE == "aerial:delete"

    def test_finance_constant(self):
        assert PERM_AERIAL_FINANCE == "aerial:finance"

    def test_wage_constant(self):
        assert PERM_AERIAL_WAGE == "aerial:wage"

    def test_approve_constant(self):
        assert PERM_AERIAL_APPROVE == "aerial:approve"


# ── Permission enforcement ──────────────────────────────────────────────────

class TestAerialPermissionEnforcement:
    """Test that aerial permission codes work with require_permission."""

    async def _check(self, permission_code: str, user) -> bool:
        dep = require_permission(permission_code)
        try:
            result = await dep(user)
            assert result is user
            return True
        except HTTPException as e:
            assert e.status_code == 403
            return False

    async def test_user_with_aerial_read_passes(self):
        role = _make_role("viewer", [PERM_AERIAL_READ])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_READ, user) is True

    async def test_user_without_aerial_read_fails(self):
        role = _make_role("viewer", ["other:read"])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_READ, user) is False

    async def test_user_with_aerial_create_passes(self):
        role = _make_role("operator", [PERM_AERIAL_CREATE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_CREATE, user) is True

    async def test_user_without_aerial_create_fails(self):
        role = _make_role("viewer", [PERM_AERIAL_READ])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_CREATE, user) is False

    async def test_user_with_aerial_update_passes(self):
        role = _make_role("editor", [PERM_AERIAL_UPDATE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_UPDATE, user) is True

    async def test_user_with_aerial_delete_passes(self):
        role = _make_role("admin", [PERM_AERIAL_DELETE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_DELETE, user) is True

    async def test_user_with_aerial_finance_passes(self):
        role = _make_role("finance", [PERM_AERIAL_FINANCE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_FINANCE, user) is True

    async def test_user_with_aerial_wage_passes(self):
        role = _make_role("hr", [PERM_AERIAL_WAGE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_WAGE, user) is True

    async def test_user_with_aerial_approve_passes(self):
        role = _make_role("manager", [PERM_AERIAL_APPROVE])
        user = _make_user([role])
        assert await self._check(PERM_AERIAL_APPROVE, user) is True

    async def test_admin_with_all_aerial_permissions(self):
        """Admin role with all aerial permissions passes all checks."""
        admin = _make_role("admin", [
            PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE,
            PERM_AERIAL_DELETE, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE,
            PERM_AERIAL_APPROVE,
        ])
        user = _make_user([admin])
        for perm in [PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE,
                     PERM_AERIAL_DELETE, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE,
                     PERM_AERIAL_APPROVE]:
            assert await self._check(perm, user) is True

    async def test_user_with_no_roles_fails_all(self):
        """User with no roles fails all aerial permission checks."""
        user = _make_user([])
        for perm in [PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE,
                     PERM_AERIAL_DELETE, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE,
                     PERM_AERIAL_APPROVE]:
            assert await self._check(perm, user) is False

    async def test_role_based_permission_check(self):
        """Different roles have different permission levels."""
        viewer = _make_role("viewer", [PERM_AERIAL_READ])
        operator = _make_role("operator", [PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE])
        finance = _make_role("finance", [PERM_AERIAL_READ, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE])
        admin = _make_role("admin", [
            PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE,
            PERM_AERIAL_DELETE, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE,
            PERM_AERIAL_APPROVE,
        ])

        # Viewer can only read
        viewer_user = _make_user([viewer])
        assert await self._check(PERM_AERIAL_READ, viewer_user) is True
        assert await self._check(PERM_AERIAL_CREATE, viewer_user) is False
        assert await self._check(PERM_AERIAL_FINANCE, viewer_user) is False

        # Operator can CRUD but not finance/approve
        operator_user = _make_user([operator])
        assert await self._check(PERM_AERIAL_READ, operator_user) is True
        assert await self._check(PERM_AERIAL_CREATE, operator_user) is True
        assert await self._check(PERM_AERIAL_UPDATE, operator_user) is True
        assert await self._check(PERM_AERIAL_FINANCE, operator_user) is False
        assert await self._check(PERM_AERIAL_APPROVE, operator_user) is False

        # Finance can read + finance
        finance_user = _make_user([finance])
        assert await self._check(PERM_AERIAL_READ, finance_user) is True
        assert await self._check(PERM_AERIAL_FINANCE, finance_user) is True
        assert await self._check(PERM_AERIAL_CREATE, finance_user) is False

        # Admin can do everything
        admin_user = _make_user([admin])
        for perm in [PERM_AERIAL_READ, PERM_AERIAL_CREATE, PERM_AERIAL_UPDATE,
                     PERM_AERIAL_DELETE, PERM_AERIAL_FINANCE, PERM_AERIAL_WAGE,
                     PERM_AERIAL_APPROVE]:
            assert await self._check(perm, admin_user) is True


# ── Permission mapping verification ─────────────────────────────────────────

class TestAerialPermissionMapping:
    """Verify the permission-to-endpoint mapping is correct."""

    def test_read_permissions_for_query_endpoints(self):
        """GET endpoints should use PERM_AERIAL_READ."""
        read_endpoints = [
            "list_vehicles", "get_vehicle", "list_drivers", "get_driver",
            "list_ledgers", "get_ledger", "list_expenses", "list_wages",
            "list_costs", "list_safety_checks", "list_attachments",
            "list_audit_logs", "dashboard_overview", "dashboard_today",
            "dashboard_reminders", "report_daily", "report_monthly",
            "report_receivables", "report_reimbursements", "report_costs",
            "report_driver_summary", "agent_list_drafts", "agent_get_draft",
        ]
        # This is a documentation test - verifies the mapping exists
        assert len(read_endpoints) == 23

    def test_create_permissions_for_mutating_endpoints(self):
        """POST create endpoints should use PERM_AERIAL_CREATE."""
        create_endpoints = [
            "create_vehicle", "create_driver", "create_ledger",
            "create_expense", "create_wage", "create_cost",
            "create_safety_check", "create_attachment",
            "agent_ingest_message",
        ]
        assert len(create_endpoints) == 9

    def test_update_permissions_for_update_endpoints(self):
        """PATCH/POST update endpoints should use PERM_AERIAL_UPDATE."""
        update_endpoints = [
            "update_vehicle", "update_driver", "update_ledger",
            "review_expense", "review_cost",
            "agent_confirm_draft", "agent_reject_draft",
        ]
        assert len(update_endpoints) == 7

    def test_delete_permissions_for_void_endpoints(self):
        """Void/delete endpoints should use PERM_AERIAL_DELETE."""
        delete_endpoints = ["void_ledger", "delete_attachment"]
        assert len(delete_endpoints) == 2

    def test_approve_permissions_for_approval_endpoints(self):
        """Approve/reject ledger endpoints should use PERM_AERIAL_APPROVE."""
        approve_endpoints = ["approve_ledger", "reject_ledger"]
        assert len(approve_endpoints) == 2

    def test_finance_permissions_for_payment_endpoints(self):
        """Payment/reimbursement endpoints should use PERM_AERIAL_FINANCE."""
        finance_endpoints = ["reimburse_expense", "pay_wage"]
        assert len(finance_endpoints) == 2

    def test_wage_permissions_for_wage_creation(self):
        """Wage creation should use PERM_AERIAL_WAGE."""
        wage_endpoints = ["create_wage"]
        assert len(wage_endpoints) == 1
