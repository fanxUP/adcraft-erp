"""Order editing, role retirement and multi-role permission regressions."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.authorization import AuthorizationEvaluator
from app.core.permission_catalog import (
    expand_permission_dependencies, permission_lifecycle_status, validate_permission_catalog,
)
from app.services.auth_service import AuthService
from app.services.role_service import RoleService
from scripts.seed_permissions import builtin_role_permission_codes


def user(*groups):
    return SimpleNamespace(roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in codes]) for codes in groups])


def test_commercial_edit_requires_readable_prices_but_confirmation_does_not():
    assert not validate_permission_catalog()
    incomplete = user(['order:read', 'order:update'])
    assert not AuthorizationEvaluator(incomplete).check('order:update').allowed
    full = expand_permission_dependencies({'order:update'})
    assert full == {'order:update', 'order:read', 'order:view_price', 'order_item:view_price'}
    assert AuthorizationEvaluator(user(full)).check('order:update').allowed
    assert AuthorizationEvaluator(user(['order:read', 'order:change_status'])).check('order:change_status').allowed


def test_multiple_roles_cannot_bypass_commercial_execution_conflict():
    commercial = expand_permission_dependencies({'order:create', 'order:update'})
    evaluator = AuthorizationEvaluator(user(commercial, ['design_task:read', 'design_task:update']))
    assert evaluator.check('order:update').reason_code == 'AUTHZ_COMBINATION_CONFLICT'
    assert evaluator.check('order:create').reason_code == 'AUTHZ_COMBINATION_CONFLICT'
    assert evaluator.check('design_task:read').allowed


@pytest.mark.parametrize('code', ['quote:create', 'quote:update', 'cdr_quote:convert', 'cdr_quote:approve'])
def test_retired_permissions_stay_retired_and_are_not_new_defaults(code):
    assert permission_lifecycle_status(code) == 'deprecated'
    for role in ['admin', 'sales', 'finance', 'manager']:
        assert code not in builtin_role_permission_codes(role)
    permission = SimpleNamespace(id='legacy', code=code, name=code, status='active')
    assert RoleService._serialize_permission(permission)['status'] == 'deprecated'
    assert RoleService._permission_status_issues([permission], set())
    assert not RoleService._permission_status_issues([permission], {code})


def test_pricing_rule_and_capture_related_permissions_are_not_retired():
    for code in ['quote:read', 'cdr_quote:read', 'cdr_rule_set:publish', 'cdr_customer_agreement:manage', 'ai_quote:read']:
        assert permission_lifecycle_status(code) == 'active'


@pytest.mark.asyncio
async def test_profile_returns_effective_permissions_for_incomplete_role_union():
    from uuid import uuid4
    current = user(['order:read', 'order:update'])
    current.id, current.username, current.real_name = uuid4(), 'reader', '只读'
    current.phone = current.email = None
    current.is_active, current.must_change_password = True, False
    current.roles[0].name = 'custom'
    service = AuthService(AsyncMock())
    result = MagicMock()
    result.scalar_one_or_none.return_value = current
    service.db.execute = AsyncMock(return_value=result)
    service._ensure_preferences = AsyncMock(return_value={})
    profile = await service.get_profile(current.id)
    assert profile['permissions'] == ['order:read', 'order:update']
    assert profile['effective_permissions'] == ['order:read']
