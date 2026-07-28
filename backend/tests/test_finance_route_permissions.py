"""订单与财务路由的细粒度权限契约。"""

import pytest

from app.api import orders, payments


def _route_permission(router, method: str, path: str) -> str | None:
    route = next(
        route
        for route in router.routes
        if method in route.methods and route.path == path
    )
    for dependency in route.dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) == "dependency" and closure:
            return closure[0].cell_contents
    return None


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/orders/", "order:read"),
        ("GET", "/orders/{order_id}", "order:read"),
        ("POST", "/orders/{order_id}/set-cost", "order:update"),
        ("POST", "/orders/{order_id}/auto-cost", "order:update"),
        ("DELETE", "/orders/{order_id}", "order:delete"),
        ("POST", "/orders/{order_id}/restore", "order:delete"),
    ],
)
def test_order_routes_require_business_permissions(method, path, permission):
    assert _route_permission(orders.router, method, path) == permission


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/expenses/", "expense:read"),
        ("GET", "/expenses/{expense_id}", "expense:read"),
        ("POST", "/expenses/", "expense:create"),
        ("PUT", "/expenses/{expense_id}", "expense:update"),
        ("DELETE", "/expenses/{expense_id}", "expense:delete"),
    ],
)
def test_expense_routes_require_business_permissions(method, path, permission):
    assert _route_permission(payments.exp_router, method, path) == permission


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/project-costs/", "expense:read"),
        ("GET", "/project-costs/summary", "expense:read"),
        ("GET", "/project-costs/template", "expense:read"),
        ("GET", "/project-costs/quotes", "expense:read"),
        ("GET", "/project-costs/debts/list", "expense:read"),
        ("GET", "/project-costs/{cost_id}", "expense:read"),
        ("GET", "/project-costs/{cost_id}/attachments", "expense:read"),
        ("POST", "/project-costs/", "expense:create"),
        ("POST", "/project-costs/import", "expense:create"),
        ("PUT", "/project-costs/{cost_id}", "expense:update"),
        ("POST", "/project-costs/{cost_id}/settle-debt", "expense:update"),
        ("POST", "/project-costs/{cost_id}/upload", "expense:update"),
        ("DELETE", "/project-costs/batch", "expense:delete"),
        ("DELETE", "/project-costs/{cost_id}", "expense:delete"),
        ("DELETE", "/project-costs/attachments/{attachment_id}", "expense:delete"),
    ],
)
def test_project_cost_routes_require_expense_permissions(method, path, permission):
    assert _route_permission(payments.cost_router, method, path) == permission
