"""Regression coverage for the built-in manager operational read-only role."""

from types import SimpleNamespace

from app.core.authorization import AuthorizationEvaluator
from app.core.permission_catalog import get_permission_definition, get_permission_pack
from app.core.permissions import (
    PERM_DASHBOARD_READ,
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_DESIGN_TASK_READ,
    PERM_FINANCE_VIEW_COST,
    PERM_INSTALLATION_TASK_READ,
    PERM_ORDER_READ,
    PERM_ORDER_VIEW_PRICE,
    PERM_PRODUCTION_TASK_READ,
    PERM_REPORT_READ,
    PERM_REPORT_VIEW_FINANCIAL,
    PERM_TASK_COMPLETION_READ,
    PERM_TASK_COMPLETION_VIEW_ALL,
    PERM_TASK_QUEUE_READ,
    PERM_TASK_QUEUE_VIEW_ALL,
    ROLE_MANAGER,
)
from app.services.order_task_assignment_service import can_view_all_task_scope
from app.services.report_service import ReportService


def _user(*permission_codes: str):
    return SimpleNamespace(
        roles=[
            SimpleNamespace(
                name=ROLE_MANAGER,
                permissions=[SimpleNamespace(code=code) for code in permission_codes],
            )
        ]
    )


def test_manager_builtin_role_is_seeded_with_operational_read_only_capabilities():
    from scripts.seed_permissions import ROLE_NAMES, ROLE_PERMISSION_MAP

    assert ROLE_MANAGER in ROLE_NAMES
    manager_permissions = set(ROLE_PERMISSION_MAP[ROLE_MANAGER])
    expected = {
        PERM_DASHBOARD_READ,
        PERM_REPORT_READ,
        PERM_ORDER_READ,
        PERM_TASK_QUEUE_READ,
        PERM_TASK_QUEUE_VIEW_ALL,
        PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_READ,
        PERM_TASK_COMPLETION_READ,
        PERM_TASK_COMPLETION_VIEW_ALL,
    }
    assert expected <= manager_permissions
    assert not manager_permissions.intersection({
        PERM_ORDER_VIEW_PRICE,
        PERM_FINANCE_VIEW_COST,
        PERM_REPORT_VIEW_FINANCIAL,
        PERM_DESIGN_TASK_CHANGE_STATUS,
        "production_task:change_status",
        "installation_task:change_status",
    })


def test_manager_permission_pack_and_report_read_sensitivity_are_non_financial():
    pack = get_permission_pack("manager_operational_readonly")

    assert PERM_DASHBOARD_READ in pack.permissions
    assert PERM_TASK_COMPLETION_VIEW_ALL in pack.permissions
    assert get_permission_definition(PERM_REPORT_READ).sensitivity == "normal"
    assert get_permission_definition(PERM_REPORT_VIEW_FINANCIAL).sensitivity == "financial"


def test_manager_can_read_operations_but_cannot_read_financial_fields_or_mutate_tasks():
    viewer = _user(
        PERM_DASHBOARD_READ,
        PERM_REPORT_READ,
        PERM_ORDER_READ,
        PERM_TASK_QUEUE_READ,
        PERM_TASK_QUEUE_VIEW_ALL,
        PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_READ,
        PERM_TASK_COMPLETION_READ,
        PERM_TASK_COMPLETION_VIEW_ALL,
    )
    evaluator = AuthorizationEvaluator(viewer)

    assert evaluator.check(PERM_DASHBOARD_READ).allowed
    assert evaluator.check(PERM_REPORT_READ).allowed
    assert evaluator.check(PERM_ORDER_READ).allowed
    assert evaluator.check(PERM_TASK_COMPLETION_VIEW_ALL).allowed
    assert not evaluator.check(PERM_ORDER_VIEW_PRICE).allowed
    assert not evaluator.check(PERM_FINANCE_VIEW_COST).allowed
    assert not evaluator.check(PERM_REPORT_VIEW_FINANCIAL).allowed
    assert not evaluator.check(PERM_DESIGN_TASK_CHANGE_STATUS).allowed


def test_manager_can_view_all_order_task_scope_without_assignment_management():
    viewer = _user(PERM_TASK_QUEUE_READ, PERM_TASK_QUEUE_VIEW_ALL)

    assert can_view_all_task_scope(viewer) is True
    assert not AuthorizationEvaluator(viewer).check("order:task_assign").allowed


def test_task_scope_permission_does_not_bypass_for_a_regular_task_reader():
    viewer = _user(PERM_TASK_QUEUE_READ)

    assert can_view_all_task_scope(viewer) is False


def test_report_service_separates_operational_and_financial_report_access():
    viewer = _user(PERM_REPORT_READ)
    service = ReportService(None, viewer=viewer)

    assert service.can_view_report is True
    assert service.can_view_financial is False


def test_operational_daily_report_does_not_return_financial_fields():
    viewer = _user(PERM_REPORT_READ)
    service = ReportService(None, viewer=viewer)
    service._list_orders_in_range = _async_result([
        SimpleNamespace(
            id="order-1",
            doc_type="order",
            doc_no="O20260913-0001",
            project_name="运营项目",
            customer_name="客户A",
            customer=None,
            department="项目部",
            status="in_progress",
            total_amount=1000,
            paid_amount=300,
            unpaid_amount=700,
        ),
    ])
    service._list_payments_in_range = _async_result([])
    service._count_new_customers = _async_result(2)

    import asyncio

    report = asyncio.run(service.get_daily_report("2026-09-13"))

    assert report["order_count"] == 1
    assert report["order_amount"] is None
    assert report["payment_count"] is None
    assert report["payment_amount"] is None
    assert report["payments"] == []
    assert "total_amount" not in report["orders"][0]


def _async_result(value):
    async def result(*_args, **_kwargs):
        return value

    return result
