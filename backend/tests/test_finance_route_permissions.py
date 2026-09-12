"""订单与财务路由的细粒度权限契约。"""

import inspect

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


def _route_permission_tuple(router, method: str, path: str) -> tuple[str, ...]:
    route = next(
        route
        for route in router.routes
        if method in route.methods and route.path == path
    )
    for dependency in route.dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) != "dependency" or not closure:
            continue
        for cell in closure:
            value = cell.cell_contents
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    return ()


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/orders/", "order:read"),
        ("GET", "/orders/{order_id}", "order:read"),
        ("GET", "/orders/{order_id}/task-attachments", "order:read"),
        ("POST", "/orders/{order_id}/task-attachments", "order:read"),
        ("GET", "/orders/{order_id}/task-attachments/{attachment_id}/file", "order:read"),
        ("DELETE", "/orders/{order_id}/task-attachments/{attachment_id}", "order:read"),
        ("GET", "/orders/{order_id}/items/editability", "order:read"),
        ("GET", "/orders/{order_id}/items/change-batches", "order:read"),
        ("GET", "/orders/{order_id}/items/change-batches/{change_batch_id}", "order:read"),
        ("GET", "/orders/{order_id}/items/reconciliation", "order:read"),
        ("POST", "/orders/{order_id}/items/preview", "order:update"),
        ("POST", "/orders/{order_id}/items", "order:update"),
        ("PATCH", "/orders/{order_id}/items/{item_id}", "order:update"),
        ("DELETE", "/orders/{order_id}/items/{item_id}", "order:update"),
        ("POST", "/orders/{order_id}/set-cost", "order:update"),
        ("POST", "/orders/{order_id}/auto-cost", "order:update"),
        ("DELETE", "/orders/{order_id}", "order:delete"),
        ("POST", "/orders/{order_id}/restore", "order:delete"),
    ],
)
def test_order_routes_require_business_permissions(method, path, permission):
    assert _route_permission(orders.router, method, path) == permission


@pytest.mark.parametrize(
    ("method", "path", "permissions"),
    [
        (
            "GET",
            "/orders/{order_id}/attachments",
            (
                "order:read",
                "design_task:read",
                "production_task:read",
                "installation_task:read",
                "task_completion:read",
            ),
        ),
        (
            "POST",
            "/orders/{order_id}/attachments",
            (
                "order:read",
                "design_task:update",
                "production_task:update",
                "installation_task:update",
            ),
        ),
        (
            "GET",
            "/orders/{order_id}/attachments/{attachment_id}/file",
            (
                "order:read",
                "design_task:read",
                "production_task:read",
                "installation_task:read",
                "task_completion:read",
            ),
        ),
        (
            "DELETE",
            "/orders/{order_id}/attachments/{attachment_id}",
            (
                "order:read",
                "design_task:update",
                "production_task:update",
                "installation_task:update",
            ),
        ),
    ],
)
def test_canonical_order_material_routes_have_stage_aware_permissions(method, path, permissions):
    assert _route_permission_tuple(orders.router, method, path) == permissions


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
        ("GET", "/project-costs/orders/{order_id}/item-summary", "expense:read"),
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


def test_project_cost_mutations_keep_operation_log_contract():
    handlers = (
        payments.create_project_cost,
        payments.update_project_cost,
        payments.batch_delete_project_costs,
        payments.delete_project_cost,
        payments.import_project_costs,
        payments.settle_cost_debt,
    )

    for handler in handlers:
        source = inspect.getsource(handler)
        assert "log_operation" in source
        assert "OBJ_PROJECT_COST" in source
