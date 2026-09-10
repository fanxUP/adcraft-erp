"""Regression tests for report nested-order price visibility."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.report_service import ReportService


def make_viewer(*permission_codes: str):
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    return SimpleNamespace(roles=[SimpleNamespace(permissions=permissions)])


def make_order():
    order = MagicMock()
    order.id = "order-1"
    order.doc_type = "order"
    order.doc_no = "O20260910-0001"
    order.project_name = "项目A"
    order.customer_name = "客户A"
    order.customer = None
    order.department = "设计部"
    order.status = "confirmed"
    order.total_amount = 1000
    order.paid_amount = 100
    order.unpaid_amount = 900
    return order


@pytest.mark.asyncio
async def test_daily_report_nested_order_reference_uses_viewer_permissions():
    service = ReportService(
        AsyncMock(),
        viewer=make_viewer("report:view_financial"),
    )
    service._list_orders_in_range = AsyncMock(return_value=[make_order()])
    service._list_payments_in_range = AsyncMock(return_value=[])
    service._count_new_customers = AsyncMock(return_value=0)

    with pytest.MonkeyPatch.context() as monkeypatch:
        vehicle_service = MagicMock()
        vehicle_service.get_daily_report = AsyncMock(return_value={})
        monkeypatch.setattr(
            "app.services.report_service.VehicleDashboardService",
            MagicMock(return_value=vehicle_service),
        )
        report = await service.get_daily_report("2026-09-10")

    assert "total_amount" not in report["orders"][0]
