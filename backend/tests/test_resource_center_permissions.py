"""Permission contracts for the resource-center APIs.

The resource center has several routers, so a login-only dependency can easily
slip in when a new endpoint is added. These tests inspect the FastAPI route
dependencies and keep the API layer as the authoritative authorization gate.
"""

from app.api import inventory, vehicles
from app.main import app
from app.core.permissions import (
    PERM_FINANCE_REVIEW,
    PERM_INVENTORY_CREATE,
    PERM_INVENTORY_READ,
    PERM_INVENTORY_STOCK_IN,
    PERM_INVENTORY_STOCK_OUT,
    PERM_INVENTORY_UPDATE,
    PERM_RESOURCE_CENTER_READ,
    PERM_VEHICLE_CREATE,
    PERM_VEHICLE_DELETE,
    PERM_VEHICLE_READ,
    PERM_VEHICLE_UPDATE,
)


def _dependency_permission_codes(dependant) -> set[str]:
    codes: set[str] = set()
    for dependency in dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) == "dependency" and closure:
            codes.update(
                cell.cell_contents
                for cell in closure
                if isinstance(cell.cell_contents, str)
            )
        codes.update(_dependency_permission_codes(dependency))
    return codes


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
            for cell in closure:
                if isinstance(cell.cell_contents, str):
                    return cell.cell_contents
    return None


def test_inventory_routes_use_action_permissions():
    expected = {
        ("GET", "/inventory/items"): PERM_INVENTORY_READ,
        ("GET", "/inventory/items/{item_id}"): PERM_INVENTORY_READ,
        ("POST", "/inventory/items"): PERM_INVENTORY_CREATE,
        ("PUT", "/inventory/items/{item_id}"): PERM_INVENTORY_UPDATE,
        ("GET", "/inventory/records"): PERM_INVENTORY_READ,
        ("POST", "/inventory/stock-in"): PERM_INVENTORY_STOCK_IN,
        ("POST", "/inventory/stock-out"): PERM_INVENTORY_STOCK_OUT,
    }

    for (method, path), permission in expected.items():
        assert _route_permission(inventory.router, method, path) == permission


def test_all_vehicle_routers_require_a_resource_permission():
    routers = (
        vehicles.router,
        vehicles.driver_router,
        vehicles.request_router,
        vehicles.dispatch_router,
        vehicles.trip_router,
        vehicles.fuel_router,
        vehicles.maintenance_router,
        vehicles.cost_router,
        vehicles.certificate_router,
        vehicles.incident_router,
        vehicles.report_router,
    )
    allowed = {
        PERM_VEHICLE_READ,
        PERM_VEHICLE_CREATE,
        PERM_VEHICLE_UPDATE,
        PERM_VEHICLE_DELETE,
        PERM_FINANCE_REVIEW,
    }

    for router in routers:
        for route in router.routes:
            permissions = {
                cell.cell_contents
                for dependency in route.dependant.dependencies
                for cell in (getattr(dependency.call, "__closure__", None) or ())
                if getattr(dependency.call, "__name__", None) == "dependency"
                and isinstance(cell.cell_contents, str)
            }
            assert permissions & allowed, f"{route.path} has no resource permission"


def test_vehicle_read_and_mutation_routes_keep_expected_boundaries():
    assert _route_permission(vehicles.router, "GET", "/vehicles/") == PERM_VEHICLE_READ
    assert _route_permission(vehicles.router, "GET", "/vehicles/{vehicle_id}") == PERM_VEHICLE_READ
    assert _route_permission(vehicles.router, "POST", "/vehicles/") == PERM_VEHICLE_CREATE
    assert _route_permission(vehicles.router, "PATCH", "/vehicles/{vehicle_id}") == PERM_VEHICLE_UPDATE
    assert _route_permission(vehicles.router, "DELETE", "/vehicles/{vehicle_id}") == PERM_VEHICLE_DELETE
    assert _route_permission(vehicles.fuel_router, "POST", "/vehicle-fuel-records/") == PERM_VEHICLE_CREATE
    assert _route_permission(vehicles.fuel_router, "POST", "/vehicle-fuel-records/{record_id}/review") == PERM_FINANCE_REVIEW


def test_all_resource_center_app_routes_require_the_parent_permission():
    resource_routes = []
    for route in app.routes:
        contexts = route.effective_route_contexts() if hasattr(route, "effective_route_contexts") else ()
        resource_routes.extend(
            context
            for context in contexts
            if context.path.startswith(("/api/v1/vehicle", "/api/v1/aerial"))
        )
    assert resource_routes

    for route in resource_routes:
        assert PERM_RESOURCE_CENTER_READ in _dependency_permission_codes(route.dependant), route.path
