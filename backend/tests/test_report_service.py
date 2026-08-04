"""Tests for ReportService: dashboard, daily/monthly reports, customer debt."""

from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.models.customer  # noqa: F401 - ensure mappers load
import app.models.business_document  # noqa: F401
import app.models.payment  # noqa: F401
import app.models.task  # noqa: F401
from app.services.report_service import ReportService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_CUSTOMER_ID, MockResult


SAMPLE_CONTRACT_ID = UUID("55555555-5555-5555-5555-555555555555")
SAMPLE_ORDER_ID = UUID("66666666-6666-6666-6666-666666666666")
SAMPLE_PROJECT_ID = UUID("77777777-7777-7777-7777-777777777777")


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


# ── get_customer_debt 测试辅助 ───────────────────────────────

def make_row(**kwargs):
    """SQLAlchemy Row 风格 mock：支持属性访问（如 last_payment）。"""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


def make_mock_customer(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", SAMPLE_CUSTOMER_ID)
    c.name = kwargs.get("name", "测试客户")
    c.deleted_at = None
    return c


def make_mock_doc(**kwargs):
    """模拟一条 order/quote 类型的 business_document（满足 _to_ref 所需字段）。"""
    d = MagicMock()
    d.id = kwargs.get("id", SAMPLE_ORDER_ID)
    d.doc_type = kwargs.get("doc_type", "order")
    d.doc_no = kwargs.get("doc_no", "O20260804-0001")
    d.project_name = kwargs.get("project_name", "测试项目")
    d.customer_name = kwargs.get("customer_name", "测试客户")
    d.customer = None
    d.department = kwargs.get("department", "工程部")
    d.status = kwargs.get("status", "completed")
    d.total_amount = kwargs.get("total_amount", 100.0)
    d.paid_amount = kwargs.get("paid_amount", 0.0)
    d.unpaid_amount = kwargs.get("unpaid_amount", 100.0)
    d.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    return d


def make_mock_contract(**kwargs):
    ct = MagicMock()
    ct.id = kwargs.get("id", SAMPLE_CONTRACT_ID)
    ct.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    ct.contract_type = kwargs.get("contract_type", "制作合同")
    ct.contract_no = kwargs.get("contract_no", "HT20260804-0001")
    ct.project_name = kwargs.get("project_name", "测试合同")
    ct.total_amount = kwargs.get("total_amount", 100.0)
    ct.status = kwargs.get("status", "active")
    ct.deleted_at = None
    ct.documents = kwargs.get("documents", [])
    return ct


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

    # Mock _customer_debt_ranking db.execute (last 3 calls): 常规关联、框架关联、客户名
    debt_result = make_all_result([(SAMPLE_CUSTOMER_ID, 50000.0)])
    fw_debt_result = make_all_result([])
    mock_customer = MagicMock()
    mock_customer.id = SAMPLE_CUSTOMER_ID
    mock_customer.name = "测试客户"
    customer_result = make_scalars_result([mock_customer])
    db.execute = AsyncMock(side_effect=results + [debt_result, fw_debt_result, customer_result])

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

    with patch(
        "app.services.report_service.VehicleDashboardService"
    ) as vehicle_service:
        vehicle_service.return_value.get_daily_report = AsyncMock(return_value={})
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
    """Customer debt ranking returns customer names."""
    svc, db = service
    customer = MagicMock()
    customer.id = SAMPLE_CUSTOMER_ID
    customer.name = "测试客户"
    results = [
        make_all_result([(SAMPLE_CUSTOMER_ID, 50000.0)]),  # 常规合同关联订单
        make_all_result([]),                               # 框架合同关联订单
        make_scalars_result([customer]),                   # 客户名
    ]
    db.execute = AsyncMock(side_effect=results)

    debts = await svc._customer_debt_ranking()
    assert len(debts) == 1
    assert debts[0]["customer_name"] is not None
    assert debts[0]["debt_amount"] == 50000.0


@pytest.mark.asyncio
async def test_customer_debt_ranking_merges_framework_linked(service):
    """首页欠款排行：框架合同关联订单计入，并与常规合同金额合并。"""
    svc, db = service
    customer = MagicMock()
    customer.id = SAMPLE_CUSTOMER_ID
    customer.name = "测试客户"
    db.execute = AsyncMock(side_effect=[
        make_all_result([(SAMPLE_CUSTOMER_ID, 10000.0)]),  # 常规
        make_all_result([(SAMPLE_CUSTOMER_ID, 20000.0)]),  # 框架
        make_scalars_result([customer]),
    ])

    debts = await svc._customer_debt_ranking()
    assert len(debts) == 1
    assert debts[0]["debt_amount"] == 30000.0


# ── get_customer_debt：应收管理只保留有合同的客户 ─────────────────

@pytest.mark.asyncio
async def test_get_customer_debt_excludes_quote_only_customer(service):
    """只有报价单、没有合同的客户不出现在应收管理中。"""
    svc, db = service
    cust = make_mock_customer()
    quote = make_mock_doc(doc_type="quote", doc_no="Q20260804-0001", status="draft")
    db.execute = AsyncMock(side_effect=[
        make_scalars_result([cust]),   # customers
        make_scalars_result([]),       # contracts
        make_scalars_result([]),       # orders
        make_scalars_result([quote]),  # quotes
        make_all_result([]),           # last_payments
    ])

    debts = await svc.get_customer_debt()
    assert debts == []


@pytest.mark.asyncio
async def test_get_customer_debt_excludes_order_without_contract(service):
    """有订单但没合同的客户不出现在应收管理中。"""
    svc, db = service
    cust = make_mock_customer()
    order = make_mock_doc(doc_no="O20260804-0001")
    db.execute = AsyncMock(side_effect=[
        make_scalars_result([cust]),
        make_scalars_result([]),       # contracts
        make_scalars_result([order]),  # orders
        make_scalars_result([]),       # quotes
        make_all_result([]),           # last_payments
    ])

    debts = await svc.get_customer_debt()
    assert debts == []


@pytest.mark.asyncio
async def test_get_customer_debt_contract_only_fields(service):
    """有合同的客户出现在应收管理，响应不含独立订单/报价字段。"""
    svc, db = service
    cust = make_mock_customer()
    order = make_mock_doc(doc_no="O20260804-0001", total_amount=100.0,
                          paid_amount=50.0, unpaid_amount=50.0)
    ct = make_mock_contract(documents=[order])
    db.execute = AsyncMock(side_effect=[
        make_scalars_result([cust]),
        make_scalars_result([ct]),       # contracts
        make_scalars_result([order]),    # orders
        make_scalars_result([]),         # quotes
        make_all_result([make_row(customer_id=SAMPLE_CUSTOMER_ID,
                                  last_payment=datetime(2026, 8, 1, tzinfo=timezone.utc))]),
        make_all_result([(SAMPLE_CONTRACT_ID, 50.0)]),  # paid_map 常规
    ])

    debts = await svc.get_customer_debt()
    assert len(debts) == 1
    item = debts[0]
    assert item["customer_id"] == str(SAMPLE_CUSTOMER_ID)
    assert item["debt_amount"] == 50.0          # 100 - 50
    assert item["total_paid"] == 50.0
    assert item["contract_count"] == 1
    assert item["last_payment_date"] is not None
    # 独立订单/报价字段已移除
    assert "order_count" not in item
    assert "quote_count" not in item
    assert "orders" not in item
    assert "quotes" not in item
    assert len(item["contracts"][0]["orders"]) == 1
    assert item["contracts"][0]["orders"][0]["order_no"] == "O20260804-0001"


@pytest.mark.asyncio
async def test_get_customer_debt_ignores_standalone_order(service):
    """有合同客户的未关联独立订单不再出现在应收管理中。"""
    svc, db = service
    cust = make_mock_customer()
    linked = make_mock_doc(doc_no="O20260804-0001")
    standalone = make_mock_doc(doc_no="O20260804-0002", total_amount=50000.0)
    ct = make_mock_contract(documents=[linked])  # 只关联 linked
    db.execute = AsyncMock(side_effect=[
        make_scalars_result([cust]),
        make_scalars_result([ct]),
        make_scalars_result([linked, standalone]),  # orders
        make_scalars_result([]),                    # quotes
        make_all_result([]),                        # last_payments
        make_all_result([(SAMPLE_CONTRACT_ID, 0.0)]),  # paid_map
    ])

    debts = await svc.get_customer_debt()
    assert len(debts) == 1
    ct_orders = debts[0]["contracts"][0]["orders"]
    assert [o["order_no"] for o in ct_orders] == ["O20260804-0001"]
    assert "orders" not in debts[0]  # 客户级独立订单字段不存在


@pytest.mark.asyncio
async def test_get_customer_debt_framework_contract(service):
    """框架合同客户：金额=项目合计，收款=项目关联单据收款，单据挂在合同下。"""
    svc, db = service
    cust = make_mock_customer()
    order = make_mock_doc(doc_no="O20260804-0001", total_amount=1000.0)
    ct = make_mock_contract(contract_type="框架合同", total_amount=0.0)
    db.execute = AsyncMock(side_effect=[
        make_scalars_result([cust]),
        make_scalars_result([ct]),
        make_scalars_result([order]),
        make_scalars_result([]),                              # quotes
        make_all_result([]),                                  # last_payments
        make_all_result([(SAMPLE_CONTRACT_ID, order.id)]),    # fcpd → fw_doc_ids_by_contract
        make_all_result([]),                                  # paid_map 常规
        make_all_result([(SAMPLE_CONTRACT_ID, 600.0)]),       # paid_map 框架
        make_all_result([(SAMPLE_CONTRACT_ID, 1000.0)]),      # fw_total
    ])

    debts = await svc.get_customer_debt()
    assert len(debts) == 1
    item = debts[0]
    assert item["debt_amount"] == 400.0  # 1000 - 600
    assert item["total_order_amount"] == 1000.0
    ct_orders = item["contracts"][0]["orders"]
    assert [o["order_no"] for o in ct_orders] == ["O20260804-0001"]
