"""供应商模块必须同时受模块入口和原子动作权限保护。"""

from app.api import suppliers
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
    assert _route_permissions("GET", "/suppliers/") == {parent, PERM_SUPPLIER_READ}
    assert _route_permissions("GET", "/suppliers/{supplier_id}") == {parent, PERM_SUPPLIER_READ}
    assert _route_permissions("POST", "/suppliers/") == {parent, PERM_SUPPLIER_CREATE}
    assert _route_permissions("PUT", "/suppliers/{supplier_id}") == {parent, PERM_SUPPLIER_UPDATE}
    assert _route_permissions("POST", "/suppliers/{supplier_id}/deactivate") == {
        parent,
        PERM_SUPPLIER_UPDATE,
    }
