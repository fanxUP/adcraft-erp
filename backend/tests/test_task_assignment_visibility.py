"""TAV-P01 tests for order-scoped task visibility and employee ownership."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api import tasks as task_api
from app.core.permissions import (
    PERM_DESIGN_TASK_ASSIGN,
    PERM_DESIGN_TASK_LIST,
    PERM_DESIGN_TASK_READ,
    PERM_INSTALLATION_TASK_ASSIGN,
    PERM_INSTALLATION_TASK_LIST,
    PERM_INSTALLATION_TASK_READ,
    PERM_ORDER_TASK_ASSIGN,
    PERM_PRODUCTION_TASK_ASSIGN,
    PERM_PRODUCTION_TASK_LIST,
    PERM_PRODUCTION_TASK_READ,
    PERM_TASK_QUEUE_READ,
    user_has_permission,
)
from app.models.task import DesignTask
from app.models.vehicle import Vehicle  # noqa: F401  # register Attachment.vehicle before mapper configuration
from app.services.order_task_assignment_service import (
    can_assign_task,
    order_task_visibility_clause,
    resolve_current_employee_user_id,
)
from app.services.task_queue_service import can_view_task_stage
from app.services.task_service import _resolve_status_assignee


VIEWER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _viewer(*permission_codes: str):
    role = MagicMock()
    codes = list(permission_codes)
    stage_by_action = {
        PERM_DESIGN_TASK_ASSIGN: PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_ASSIGN: PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_ASSIGN: PERM_INSTALLATION_TASK_READ,
    }
    for action, read in stage_by_action.items():
        if action in codes and read not in codes:
            codes.append(read)
    if PERM_ORDER_TASK_ASSIGN in codes and "order:read" not in codes:
        codes.append("order:read")
    role.permissions = [MagicMock(code=code) for code in codes]
    viewer = MagicMock(id=VIEWER_ID)
    viewer.roles = [role]
    return viewer


def test_new_task_permissions_are_explicit_and_not_implied_by_stage_read():
    viewer = _viewer("design_task:read")

    assert user_has_permission(viewer, "design_task:read") is True
    assert user_has_permission(viewer, PERM_TASK_QUEUE_READ) is False
    assert can_assign_task("design", viewer) is False

    manager = _viewer(PERM_DESIGN_TASK_ASSIGN, PERM_ORDER_TASK_ASSIGN)
    assert can_assign_task("design", manager) is True
    assert user_has_permission(manager, PERM_ORDER_TASK_ASSIGN) is True


def test_task_queue_respects_stage_read_permissions_when_roles_are_composed():
    viewer = _viewer(PERM_TASK_QUEUE_READ, PERM_DESIGN_TASK_READ)

    assert can_view_task_stage("design", viewer) is True
    assert can_view_task_stage("production", viewer) is False
    assert can_view_task_stage("installation", viewer) is False


def test_order_visibility_clause_has_unassigned_or_current_employee_branches():
    viewer = _viewer(PERM_TASK_QUEUE_READ)
    statement = select(DesignTask.__table__).where(order_task_visibility_clause(DesignTask, viewer))
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "order_task_assignees" in sql
    assert "employees" in sql
    assert "design_tasks.document_id" in sql


def _route_permissions(router, method: str, path: str) -> set[str]:
    permissions: set[str] = set()
    for route in router.routes:
        if path != route.path or method.upper() not in route.methods:
            continue
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) == "dependency" and closure:
                permissions.update(
                    cell.cell_contents
                    for cell in closure
                    if isinstance(cell.cell_contents, str) and ":" in cell.cell_contents
                )
    return permissions


def test_task_lists_and_assignment_actions_have_separate_route_permissions():
    assert _route_permissions(task_api.design_router, "GET", "/design-tasks/") == {PERM_DESIGN_TASK_LIST}
    assert _route_permissions(task_api.design_router, "GET", "/design-tasks/{task_id}") == {PERM_DESIGN_TASK_READ}
    assert _route_permissions(task_api.design_router, "PUT", "/design-tasks/{task_id}/assignee") == {PERM_DESIGN_TASK_ASSIGN}

    assert _route_permissions(task_api.prod_router, "GET", "/production-tasks/") == {PERM_PRODUCTION_TASK_LIST}
    assert _route_permissions(task_api.prod_router, "GET", "/production-tasks/{task_id}") == {PERM_PRODUCTION_TASK_READ}
    assert _route_permissions(task_api.prod_router, "PUT", "/production-tasks/{task_id}/assignee") == {PERM_PRODUCTION_TASK_ASSIGN}

    assert _route_permissions(task_api.inst_router, "GET", "/installation-tasks/") == {PERM_INSTALLATION_TASK_LIST}
    assert _route_permissions(task_api.inst_router, "GET", "/installation-tasks/{task_id}") == {PERM_INSTALLATION_TASK_READ}
    assert _route_permissions(task_api.inst_router, "PUT", "/installation-tasks/{task_id}/assignee") == {PERM_INSTALLATION_TASK_ASSIGN}


@pytest.mark.asyncio
async def test_status_owner_must_resolve_to_an_active_employee_binding():
    employee = MagicMock()
    employee.user_id = VIEWER_ID
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=employee)))

    assert await resolve_current_employee_user_id(db, _viewer(PERM_TASK_QUEUE_READ)) == VIEWER_ID


@pytest.mark.asyncio
async def test_unbound_status_owner_gets_plain_language_error():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(ValueError, match="未绑定在职员工"):
        await resolve_current_employee_user_id(db, _viewer(PERM_TASK_QUEUE_READ))


@pytest.mark.asyncio
async def test_status_change_rejects_whole_task_owner_override():
    task = MagicMock(assigned_to=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))

    with pytest.raises(ValueError, match="不再设置整张任务负责人"):
        await _resolve_status_assignee(
            MagicMock(),
            task,
            str(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")),
            task_type="design",
            viewer=_viewer(PERM_TASK_QUEUE_READ),
        )


@pytest.mark.asyncio
async def test_order_item_options_require_the_matching_stage_detail_permission():
    with pytest.raises(HTTPException) as exc_info:
        await task_api.list_task_order_item_options(
            task_type="design",
            task_id=str(UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")),
            db=MagicMock(),
            current_user=_viewer(PERM_TASK_QUEUE_READ),
        )

    assert exc_info.value.status_code == 403
    assert "任务详情" in exc_info.value.detail
