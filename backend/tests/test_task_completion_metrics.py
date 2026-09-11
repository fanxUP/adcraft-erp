"""TCD-P01: completion-event, period, permission and response-contract tests."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.permission_catalog import get_permission_definition, get_permission_dependencies
from app.core.permissions import (
    PERM_TASK_COMPLETION_READ,
    PERM_TASK_COMPLETION_VIEW_ALL,
)
from app.api import reports
from app.models.customer import Customer  # noqa: F401  # register model relationships for isolated service tests
from app.models.task_item_status_log import TaskItemStatusLog
from app.models.user import User  # noqa: F401  # register task attachment relationships
from app.models.vehicle import Vehicle  # noqa: F401  # register task attachment relationships
from app.services.task_completion_metrics_service import (
    TaskCompletionAccessError,
    TaskCompletionMetricsService,
    _select_current_completed_work_units,
    get_task_completion_period,
)
from app.services.task_service import _apply_task_item_status_change
from tests.conftest import (
    SAMPLE_ORDER_ID,
    SAMPLE_ORDER_ITEM_ID,
    SAMPLE_TASK_ID,
    SAMPLE_USER_ID,
    make_mock_design_task,
)


OTHER_ITEM_ID = UUID("66666666-6666-6666-6666-666666666666")
OTHER_USER_ID = UUID("77777777-7777-7777-7777-777777777777")
OTHER_EMPLOYEE_ID = UUID("99999999-9999-9999-9999-999999999999")


def _event(
    task_type: str,
    item_id: UUID,
    to_status: str,
    operated_at: datetime,
    *,
    task_id: UUID = SAMPLE_TASK_ID,
    document_id: UUID = SAMPLE_ORDER_ID,
    assignee_user_id: UUID | None = SAMPLE_USER_ID,
):
    return SimpleNamespace(
        id=UUID("88888888-8888-8888-8888-888888888888"),
        task_type=task_type,
        task_id=task_id,
        document_id=document_id,
        order_item_id=item_id,
        to_status=to_status,
        operated_at=operated_at,
        assignee_user_id=assignee_user_id,
    )


def test_completion_period_uses_shanghai_month_half_open_interval():
    start, end = get_task_completion_period(
        "month",
        now=datetime(2026, 9, 11, 10, 20, 30),
    )

    assert start == datetime(2026, 9, 1)
    assert end == datetime(2026, 10, 1)


def test_current_completed_work_units_ignore_rework_and_respect_period():
    events = [
        _event("design", SAMPLE_ORDER_ITEM_ID, "confirmed", datetime(2026, 9, 2, 9)),
        _event("design", SAMPLE_ORDER_ITEM_ID, "designing", datetime(2026, 9, 3, 9)),
        _event("production", OTHER_ITEM_ID, "completed", datetime(2026, 8, 31, 23, 59)),
        _event("installation", OTHER_ITEM_ID, "completed", datetime(2026, 9, 1)),
        _event(
            "production",
            SAMPLE_ORDER_ITEM_ID,
            "completed",
            datetime(2026, 9, 10, 17),
            assignee_user_id=OTHER_USER_ID,
        ),
    ]

    selected = _select_current_completed_work_units(
        events,
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        owner_user_id=OTHER_USER_ID,
    )

    assert [(event.task_type, event.order_item_id) for event in selected] == [
        ("production", SAMPLE_ORDER_ITEM_ID),
    ]

    all_time = _select_current_completed_work_units(events)
    assert {(event.task_type, event.order_item_id) for event in all_time} == {
        ("installation", OTHER_ITEM_ID),
        ("production", OTHER_ITEM_ID),
        ("production", SAMPLE_ORDER_ITEM_ID),
    }


@pytest.mark.asyncio
async def test_status_change_writes_one_event_for_each_selected_item():
    db = AsyncMock()
    db.add_all = MagicMock()
    task = make_mock_design_task(status="designing", progress_pct=50, assigned_to=SAMPLE_USER_ID)
    operator_id = OTHER_USER_ID

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[SAMPLE_ORDER_ITEM_ID, OTHER_ITEM_ID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(
                return_value={
                    SAMPLE_ORDER_ITEM_ID: ("designing", 50),
                    OTHER_ITEM_ID: ("designing", 50),
                }
            ),
        ),
    ):
        await _apply_task_item_status_change(
            db,
            "design",
            task,
            "confirmed",
            [str(SAMPLE_ORDER_ITEM_ID), str(OTHER_ITEM_ID)],
            assignee_user_id=SAMPLE_USER_ID,
            operated_by=operator_id,
        )

    events = db.add_all.call_args.args[0]
    assert len(events) == 2
    assert all(isinstance(event, TaskItemStatusLog) for event in events)
    assert {(event.order_item_id, event.from_status, event.to_status) for event in events} == {
        (SAMPLE_ORDER_ITEM_ID, "designing", "confirmed"),
        (OTHER_ITEM_ID, "designing", "confirmed"),
    }
    assert all(event.assignee_user_id == SAMPLE_USER_ID for event in events)
    assert all(event.operated_by == operator_id for event in events)


def test_completion_permissions_are_atomic_and_non_financial():
    dependencies = get_permission_dependencies(PERM_TASK_COMPLETION_VIEW_ALL)
    assert dependencies == (PERM_TASK_COMPLETION_READ,)
    assert get_permission_definition(PERM_TASK_COMPLETION_READ).sensitivity == "normal"
    assert get_permission_definition(PERM_TASK_COMPLETION_VIEW_ALL).sensitivity == "normal"


def test_completion_detail_whitelist_does_not_include_financial_fields():
    from app.services.task_completion_metrics_service import serialize_completion_detail

    payload = serialize_completion_detail(
        project_id=SAMPLE_ORDER_ID,
        project_no="O20260911-0001",
        project_name="测试项目",
        item_id=SAMPLE_ORDER_ITEM_ID,
        item_name="门头字",
        task_type="production",
        task_id=SAMPLE_TASK_ID,
        task_no="P20260911-0001",
        assignee_user_id=SAMPLE_USER_ID,
        assignee_name="张三",
        completed_at=datetime(2026, 9, 10, 12),
    )

    assert payload["item_name"] == "门头字"
    assert payload["task_type"] == "production"
    assert not {
        "total_amount",
        "unit_price",
        "subtotal_amount",
        "cost_amount",
        "gross_profit",
    }.intersection(payload)


@pytest.mark.asyncio
async def test_personal_scope_rejects_another_employee_id():
    viewer = SimpleNamespace(
        id=SAMPLE_USER_ID,
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=PERM_TASK_COMPLETION_READ)])],
    )
    service = TaskCompletionMetricsService(AsyncMock(), viewer)

    with patch.object(
        service,
        "_current_employee",
        new=AsyncMock(return_value=SimpleNamespace(id=OTHER_EMPLOYEE_ID)),
    ):
        with pytest.raises(TaskCompletionAccessError, match="只能查看当前登录员工"):
            await service._resolve_scope(SAMPLE_ORDER_ITEM_ID)


def test_completion_report_routes_require_personal_read_permission():
    routes = {
        route.path: route
        for route in reports.router.routes
        if route.path in {
            "/reports/task-completion/summary",
            "/reports/task-completion/details",
        }
    }

    assert set(routes) == {
        "/reports/task-completion/summary",
        "/reports/task-completion/details",
    }
    for route in routes.values():
        permissions = set()
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) != "dependency" or not closure:
                continue
            for cell in closure:
                value = cell.cell_contents
                if isinstance(value, str) and ":" in value:
                    permissions.add(value)
        assert permissions == {PERM_TASK_COMPLETION_READ}
