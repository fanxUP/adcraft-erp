from app.api import outsource
from app.core.permissions import (
    PERM_OUTSOURCE_CREATE,
    PERM_OUTSOURCE_DELETE,
    PERM_OUTSOURCE_PAYMENT_CREATE,
    PERM_OUTSOURCE_PAYMENT_READ,
    PERM_OUTSOURCE_READ,
    PERM_OUTSOURCE_UPDATE,
)


def _route_permission(method: str, path: str) -> str | None:
    for route in outsource.router.routes:
        if path != route.path or method.upper() not in route.methods:
            continue
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) == "dependency" and closure:
                for cell in closure:
                    if isinstance(cell.cell_contents, str):
                        return cell.cell_contents
    return None


def test_outsource_routes_use_business_permissions():
    expected = {
        ("GET", "/outsource/vendors"): PERM_OUTSOURCE_READ,
        ("POST", "/outsource/vendors"): PERM_OUTSOURCE_CREATE,
        ("PUT", "/outsource/vendors/{vendor_id}"): PERM_OUTSOURCE_UPDATE,
        ("DELETE", "/outsource/vendors/{vendor_id}"): PERM_OUTSOURCE_DELETE,
        ("GET", "/outsource/tasks"): PERM_OUTSOURCE_READ,
        ("POST", "/outsource/tasks"): PERM_OUTSOURCE_CREATE,
        ("PUT", "/outsource/tasks/{task_id}"): PERM_OUTSOURCE_UPDATE,
        ("POST", "/outsource/tasks/{task_id}/cancel"): PERM_OUTSOURCE_DELETE,
        ("POST", "/outsource/tasks/{task_id}/revert"): PERM_OUTSOURCE_DELETE,
        ("DELETE", "/outsource/tasks/{task_id}"): PERM_OUTSOURCE_DELETE,
        ("GET", "/outsource/payments"): PERM_OUTSOURCE_PAYMENT_READ,
        ("POST", "/outsource/payments"): PERM_OUTSOURCE_PAYMENT_CREATE,
    }

    for (method, path), permission in expected.items():
        assert _route_permission(method, path) == permission
