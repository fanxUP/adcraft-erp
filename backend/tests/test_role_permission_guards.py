"""Regression tests for role permission safety and custom-role preservation."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.services.role_service import RoleService
from app.services.user_service import UserService
from app.core.permissions import validate_role_resource_permissions


def _role(name: str, role_id: str = "11111111-1111-1111-1111-111111111111", permissions=None):
    role = MagicMock()
    role.name = name
    role.id = UUID(role_id)
    role.permissions = [MagicMock(code=code) for code in (permissions or [])]
    return role


@pytest.mark.asyncio
async def test_role_service_rejects_partial_or_unknown_permission_ids():
    service = RoleService(AsyncMock())
    service.repo.get_by_id = AsyncMock(return_value=_role("designer"))
    service.repo.get_permissions_by_ids = AsyncMock(return_value=[])

    with pytest.raises(ValueError, match="存在无效权限编号"):
        await service.set_role_permissions(
            UUID("11111111-1111-1111-1111-111111111111"),
            ["22222222-2222-2222-2222-222222222222"],
        )


@pytest.mark.asyncio
async def test_role_service_rejects_sensitive_permissions_for_execution_role():
    service = RoleService(AsyncMock())
    service.repo.get_by_id = AsyncMock(return_value=_role("production"))
    permission = MagicMock()
    permission.id = UUID("22222222-2222-2222-2222-222222222222")
    permission.code = "order:view_price"
    permission.name = "查看订单价格"
    service.repo.get_permissions_by_ids = AsyncMock(return_value=[permission])

    with pytest.raises(ValueError, match="设计、制作、安装角色不能拥有价格或财务权限"):
        await service.set_role_permissions(
            UUID("11111111-1111-1111-1111-111111111111"),
            [str(permission.id)],
        )


@pytest.mark.asyncio
async def test_role_service_rejects_resource_permissions_for_execution_role():
    service = RoleService(AsyncMock())
    service.repo.get_by_id = AsyncMock(return_value=_role("production"))
    permission = MagicMock()
    permission.id = UUID("22222222-2222-2222-2222-222222222222")
    permission.code = "resource_center:read"
    permission.name = "进入资源中心"
    service.repo.get_permissions_by_ids = AsyncMock(return_value=[permission])

    with pytest.raises(ValueError, match="设计、制作、安装角色不能拥有资源中心权限"):
        await service.set_role_permissions(
            UUID("11111111-1111-1111-1111-111111111111"),
            [str(permission.id)],
        )


def test_execution_role_resource_permission_guard_is_explicit():
    with pytest.raises(ValueError, match="设计、制作、安装角色不能拥有资源中心权限"):
        validate_role_resource_permissions("installer", ["aerial:read"])


@pytest.mark.asyncio
async def test_user_service_rejects_mixed_execution_and_finance_roles():
    service = UserService(AsyncMock())
    service.repo.get_by_username = AsyncMock(return_value=None)
    service.repo.get_roles = AsyncMock(
        return_value=[_role("designer"), _role("finance")]
    )

    with pytest.raises(ValueError, match="执行角色不能与销售或财务角色同时分配"):
        await service.create_user({
            "username": "operator",
            "password": "Secret123!",
            "role_ids": [
                "11111111-1111-1111-1111-111111111111",
                "11111111-1111-1111-1111-111111111111",
            ],
        })


def test_user_service_rejects_custom_execution_role_with_sensitive_role_permissions():
    first_id = "11111111-1111-1111-1111-111111111111"
    second_id = "22222222-2222-2222-2222-222222222222"

    with pytest.raises(ValueError, match="执行角色不能与带价格或财务权限的角色同时分配"):
        UserService._validate_roles(
            [first_id, second_id],
            [
                _role("delivery-operator", first_id, ["production_task:read"]),
                _role("commercial-viewer", second_id, ["quote:read"]),
            ],
        )


def test_user_service_allows_sales_role_task_read_access():
    UserService._validate_roles(
        ["11111111-1111-1111-1111-111111111111"],
        [_role("sales", permissions=["design_task:read", "order:view_price"])],
    )


def test_init_script_has_an_explicit_custom_role_preservation_branch():
    from pathlib import Path

    source = (Path(__file__).parents[1] / "scripts" / "init_app.py").read_text()
    assert "if role_name not in ROLE_NAMES" in source
    assert "continue" in source
