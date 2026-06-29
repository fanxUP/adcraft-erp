"""Tests for ReportService: dashboard, daily/monthly reports, customer debt."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.models.customer  # noqa: F401 - ensure mappers load
import app.models.order  # noqa: F401
import app.models.payment  # noqa: F401
import app.models.task  # noqa: F401
from app.services.report_service import ReportService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_CUSTOMER_ID, MockResult


class MockResultWithScalar:
    """Mock SQLAlchemy result that supports both scalar() and scalar_one_or_none()."""

    def __init__(self, scalar_value=None, scalar_one_or_none_value=None):
        self._scalar_value = scalar_value
        self._scalar_one_or_none_value = scalar_one_or_none_value

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_value

    def scalars(self):
        return self

    def all(self):
        if self._scalar_value is not None and not isinstance(self._scalar_value, list):
            return [self._scalar_value]
        return self._scalar_value or []


def make_all_result(rows):
    """Create a mock result returning rows via .all()."""
    r = MagicMock()
    r.all.return_value = rows
    return r


def make_scalars_result(items):
    """Create a mock SQLAlchemy scalars result returning items via .all()."""
    r = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = items
    r.scalars.return_value = scalars_obj
    return r


def make_all_result(rows):
    """Create a mock SQLAlchemy result returning rows via .all()."""
    r = MagicMock()
    r.all.return_value = rows
    return r


@pytest.fixture
def service():
    db = AsyncMock()
    return ReportService(db), db


@pytest.mark.asyncio
async def test_get_dashboard(service):
    """Dashboard aggregates counts and amounts across models."""
    svc, db = service

    # Set up 9 sequential db.execute calls for scalar results
    results = [
        MockResultWithScalar(scalar_value=50000.0),   # today_orders
        MockResultWithScalar(scalar_value=200000.0),  # month_orders
        MockResultWithScalar(scalar_value=10000.0),   # today_payments
        MockResultWithScalar(scalar_value=80000.0),   # month_payments
        MockResultWithScalar(scalar_value=120000.0),  # month_unpaid
        MockResultWithScalar(scalar_value=3),          # pending_design
        MockResultWithScalar(scalar_value=5),          # pending_production
        MockResultWithScalar(scalar_value=2),          # pending_installation
        MockResultWithScalar(scalar_value=1),          # overdue_orders
    ]

    # Mock _customer_debt_ranking db.execute (last 2 calls) with iterable rows
    class MockRow:
        def __init__(self, cid, dbt):
            self.customer_id = cid
            self.debt = dbt
        def __iter__(self):
            return iter((self.customer_id, self.debt))

    debt_result = make_all_result([MockRow(SAMPLE_CUSTOMER_ID, 50000.0)])
    mock_customer = MagicMock()
    mock_customer.name = "测试客户"
    customer_result = MockResultWithScalar(scalar_one_or_none_value=mock_customer)
    db.execute = AsyncMock(side_effect=results + [debt_result, customer_result])

    dash = await svc.get_dashboard()

    assert dash["today_order_amount"] == 50000.0
    assert dash["month_order_amount"] == 200000.0
    assert dash["today_payment_amount"] == 10000.0
    assert dash["month_payment_amount"] == 80000.0
    assert dash["month_unpaid_amount"] == 120000.0
    assert dash["pending_design_count"] == 3
    assert dash["pending_production_count"] == 5
    assert dash["pending_installation_count"] == 2
    assert dash["overdue_order_count"] == 1
    assert len(dash["customer_debt_ranking"]) == 1


@pytest.mark.asyncio
async def test_get_daily_report(service):
    """Daily report returns orders, payments, and new customer count."""
    svc, db = service
    order1 = MagicMock()
    order1.id = SAMPLE_USER_ID
    order1.order_no = "O20260629-0001"
    order1.project_name = "测试订单"
    order1.total_amount = 5000.0
    order1.status = "confirmed"
    payment1 = MagicMock()
    payment1.id = SAMPLE_USER_ID
    payment1.payment_no = "PAY20260629-0001"
    payment1.amount = 3000.0
    payment1.payment_method = "bank_transfer"
    payment1.is_voided = False

    results = [
        make_scalars_result([order1]),          # _list_orders_in_range
        make_scalars_result([payment1]),        # _list_payments_in_range
        MockResultWithScalar(scalar_value=2),   # _count_new_customers
    ]
    db.execute = AsyncMock(side_effect=results)

    report = await svc.get_daily_report("2026-06-29")
    assert report["date"] == "2026-06-29"
    assert report["order_count"] == 1
    assert report["order_amount"] == 5000.0
    assert report["payment_count"] == 1
    assert report["payment_amount"] == 3000.0
    assert report["new_customer_count"] == 2


@pytest.mark.asyncio
async def test_get_monthly_report(service):
    """Monthly report returns aggregations with status breakdown."""
    svc, db = service
    order1 = MagicMock()
    order1.order_no = "O20260629-0001"
    order1.total_amount = 5000.0
    order1.paid_amount = 3000.0
    order1.unpaid_amount = 2000.0
    order1.status = "confirmed"
    order2 = MagicMock()
    order2.order_no = "O20260629-0002"
    order2.total_amount = 3000.0
    order2.paid_amount = 0.0
    order2.unpaid_amount = 3000.0
    order2.status = "pending_confirm"

    payment1 = MagicMock()
    payment1.amount = 3000.0

    results = [
        make_scalars_result([order1, order2]),  # _list_orders_in_range
        make_scalars_result([payment1]),        # _list_payments_in_range
    ]
    db.execute = AsyncMock(side_effect=results)

    report = await svc.get_monthly_report(2026, 6)
    assert report["year"] == 2026
    assert report["month"] == 6
    assert report["order_count"] == 2
    assert report["order_amount"] == 8000.0
    assert report["payment_count"] == 1
    assert report["payment_amount"] == 3000.0
    assert report["unpaid_amount"] == 5000.0  # 8000 - 3000
    assert report["status_breakdown"]["confirmed"] == 1
    assert report["status_breakdown"]["pending_confirm"] == 1


@pytest.mark.asyncio
async def test_get_customer_debt(service):
    """Customer debt returns ranking with customer names."""
    svc, db = service

    class MockRow:
        def __init__(self, cid, dbt):
            self.customer_id = cid
            self.debt = dbt
        def __iter__(self):
            return iter((self.customer_id, self.debt))

    results = [
        make_all_result([MockRow(SAMPLE_CUSTOMER_ID, 50000.0)]),  # group_by query
        MockResultWithScalar(scalar_one_or_none_value=MagicMock()),  # customer lookup
    ]
    db.execute = AsyncMock(side_effect=results)

    debts = await svc.get_customer_debt()
    assert len(debts) == 1
    assert debts[0]["customer_name"] is not None
    assert debts[0]["debt_amount"] == 50000.0
