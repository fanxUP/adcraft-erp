from unittest.mock import AsyncMock
from app.api import outsource
from app.core.permissions import (
    PERM_OUTSOURCE_CENTER_READ,
    PERM_OUTSOURCE_PAYMENT_CREATE,
    PERM_OUTSOURCE_PAYMENT_READ,
    PERM_OUTSOURCE_TASK_CHANGE_STATUS,
    PERM_OUTSOURCE_TASK_CREATE,
    PERM_OUTSOURCE_TASK_DELETE,
    PERM_OUTSOURCE_TASK_PERMANENT_DELETE,
    PERM_OUTSOURCE_TASK_READ,
    PERM_OUTSOURCE_TASK_UPDATE,
    PERM_OUTSOURCE_VENDOR_CREATE,
    PERM_OUTSOURCE_VENDOR_DELETE,
    PERM_OUTSOURCE_VENDOR_READ,
    PERM_OUTSOURCE_VENDOR_UPDATE,
)
from fastapi import HTTPException
from types import SimpleNamespace
from uuid import UUID
import pytest


def _route_permissions(method: str, path: str) -> set[str]:
    permissions: set[str] = set()
    for route in outsource.router.routes:
        if path != route.path or method.upper() not in route.methods:
            continue
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) == "dependency" and closure:
                for cell in closure:
                    value = cell.cell_contents
                    if isinstance(value, str) and ":" in value:
                        permissions.add(value)
                    elif isinstance(value, (tuple, list, set, frozenset)):
                        permissions.update(
                            item for item in value
                            if isinstance(item, str) and ":" in item
                        )
    return permissions


def test_outsource_routes_use_parent_and_action_permissions():
    parent = PERM_OUTSOURCE_CENTER_READ
    expected = {
        ("GET", "/outsource/vendors"): {parent, PERM_OUTSOURCE_VENDOR_READ},
        ("GET", "/outsource/vendors/{vendor_id}"): {parent, PERM_OUTSOURCE_VENDOR_READ},
        ("POST", "/outsource/vendors"): {parent, PERM_OUTSOURCE_VENDOR_CREATE},
        ("PUT", "/outsource/vendors/{vendor_id}"): {parent, PERM_OUTSOURCE_VENDOR_UPDATE},
        ("DELETE", "/outsource/vendors/{vendor_id}"): {parent, PERM_OUTSOURCE_VENDOR_DELETE},
        ("GET", "/outsource/tasks"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/task-groups"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/task-groups/{group_key}/tasks"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/orders/{order_id}/items-summary"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/orders/{order_id}/items-for-dropdown"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("POST", "/outsource/orders/{order_id}/items/{item_id}/send"): {parent, PERM_OUTSOURCE_TASK_CREATE},
        ("POST", "/outsource/tasks"): {parent, PERM_OUTSOURCE_TASK_CREATE},
        ("PUT", "/outsource/tasks/{task_id}"): {parent, PERM_OUTSOURCE_TASK_UPDATE},
        ("POST", "/outsource/tasks/{task_id}/cancel"): {parent, PERM_OUTSOURCE_TASK_CHANGE_STATUS},
        ("POST", "/outsource/tasks/{task_id}/revert"): {parent, PERM_OUTSOURCE_TASK_CHANGE_STATUS},
        ("DELETE", "/outsource/tasks/{task_id}"): {parent, PERM_OUTSOURCE_TASK_DELETE},
        ("GET", "/outsource/tasks/recycle/list"): {parent, PERM_OUTSOURCE_TASK_DELETE},
        ("POST", "/outsource/tasks/{task_id}/restore"): {parent, PERM_OUTSOURCE_TASK_DELETE},
        ("DELETE", "/outsource/tasks/recycle/{task_id}"): {
            parent,
            PERM_OUTSOURCE_TASK_DELETE,
            PERM_OUTSOURCE_TASK_PERMANENT_DELETE,
        },
        ("GET", "/outsource/quotes-for-dropdown"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/orders-for-dropdown"): {parent, PERM_OUTSOURCE_TASK_READ},
        ("GET", "/outsource/tasks/payment-summary/{task_id}"): {PERM_OUTSOURCE_PAYMENT_READ},
        ("GET", "/outsource/payments"): {PERM_OUTSOURCE_PAYMENT_READ},
        ("POST", "/outsource/payments"): {PERM_OUTSOURCE_PAYMENT_CREATE},
    }

    for (method, path), permissions in expected.items():
        assert _route_permissions(method, path) == permissions


def test_payment_routes_do_not_inherit_external_task_write_permissions():
    assert _route_permissions("GET", "/outsource/payments") == {PERM_OUTSOURCE_PAYMENT_READ}
    assert _route_permissions("POST", "/outsource/payments") == {PERM_OUTSOURCE_PAYMENT_CREATE}


def test_external_task_status_update_requires_the_separate_status_permission():
    user = SimpleNamespace(
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=PERM_OUTSOURCE_TASK_UPDATE)])]
    )

    try:
        outsource._ensure_outsource_task_status_permission(user, {"status": "completed"})
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "变更外协任务状态" in exc.detail
    else:
        raise AssertionError("缺少状态权限时不应允许修改外协任务状态")


@pytest.mark.asyncio
async def test_permanent_delete_route_records_snapshot_reason_and_actor_in_same_session(monkeypatch):
    task_id = UUID("33333333-3333-3333-3333-333333333333")
    snapshot = {"task_no": "OT20261023-0005", "status": "cancelled", "paid_amount": 0.0}
    service = SimpleNamespace(permanently_delete_task=AsyncMock(return_value={
        "task_id": str(task_id),
        "task_no": "OT20261023-0005",
        "snapshot": snapshot,
        "reason": "确认无财务影响后清理",
    }))
    db = object()
    audit = AsyncMock()
    monkeypatch.setattr(outsource, "OutsourceService", lambda session, viewer: service)
    monkeypatch.setattr(outsource, "log_operation", audit)
    request = SimpleNamespace(client=SimpleNamespace(host="192.0.2.10"))
    user = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), real_name="审计人", username="admin")

    response = await outsource.permanently_delete_task(
        task_id=task_id,
        request=request,
        task_no_confirmation="OT20261023-0005",
        reason="确认无财务影响后清理",
        db=db,
        current_user=user,
    )

    assert response["data"] == {"task_id": str(task_id), "task_no": "OT20261023-0005"}
    service.permanently_delete_task.assert_awaited_once_with(
        task_id,
        task_no_confirmation="OT20261023-0005",
        reason="确认无财务影响后清理",
    )
    audit.assert_awaited_once_with(
        db,
        user.id,
        "审计人",
        outsource.OBJ_OUTSOURCE_TASK,
        task_id,
        "permanent_delete",
        ip_address="192.0.2.10",
        before_data=snapshot,
        after_data={
            "task_no": "OT20261023-0005",
            "reason": "确认无财务影响后清理",
            "deleted": True,
        },
    )
