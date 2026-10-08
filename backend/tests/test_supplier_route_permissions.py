"""供应商模块必须同时受模块入口和原子动作权限保护。"""

from app.api import suppliers
import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from app.core.permissions import (
    PERM_SUPPLIER_CENTER_READ,
    PERM_SUPPLIER_CREATE,
    PERM_SUPPLIER_READ,
    PERM_SUPPLIER_UPDATE,
)


def _route_permissions(method: str, path: str) -> set[str]:
    permissions: set[str] = set()
    for route in suppliers.router.routes:
        if path != route.path or method.upper() not in route.methods:
            continue
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) != "dependency" or not closure:
                continue
            for cell in closure:
                value = cell.cell_contents
                if isinstance(value, str) and ":" in value:
                    permissions.add(value)
                elif isinstance(value, (tuple, list, set, frozenset)):
                    permissions.update(
                        item for item in value if isinstance(item, str) and ":" in item
                    )
    return permissions


def test_supplier_routes_use_parent_and_action_permissions():
    parent = PERM_SUPPLIER_CENTER_READ
    read = {parent, PERM_SUPPLIER_READ, "outsource_center:read", "outsource_vendor:read"}
    assert _route_permissions("GET", "/suppliers/") == read
    assert _route_permissions("GET", "/suppliers/{supplier_id}") == read
    assert _route_permissions("POST", "/suppliers/") == {parent, PERM_SUPPLIER_CREATE, "outsource_center:read", "outsource_vendor:create"}
    assert _route_permissions("PUT", "/suppliers/{supplier_id}") == {parent, PERM_SUPPLIER_UPDATE, "outsource_center:read", "outsource_vendor:update"}
    assert _route_permissions("POST", "/suppliers/{supplier_id}/deactivate") == {
        parent,
        PERM_SUPPLIER_UPDATE,
        "outsource_center:read", "outsource_vendor:update",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("codes,allowed", [
    (["supplier_center:read", "supplier:read"], True),
    (["outsource_center:read", "outsource_vendor:read"], True),
    (["supplier:read"], False), (["outsource_vendor:read"], False),
    (["supplier_center:read", "outsource_vendor:read"], False),
    (["outsource_center:read", "outsource_task:read"], False),
])
async def test_supplier_entry_requires_a_complete_permission_group(codes, allowed):
    user = SimpleNamespace(roles=[SimpleNamespace(permissions=[SimpleNamespace(code=c) for c in codes])])
    if allowed:
        assert await suppliers._READ(user) is user
    else:
        with pytest.raises(HTTPException) as error:
            await suppliers._READ(user)
        assert error.value.status_code == 403
