"""Tests for OrderService: CRUD, status change, cost calculation."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.order_service import OrderService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_ORDER_ID, SAMPLE_CUSTOMER_ID


def make_mock_order(**kwargs):
    o = MagicMock()
    o.id = kwargs.get("id", SAMPLE_ORDER_ID)
    o.order_no = kwargs.get("order_no", "O20260629-0001")
    o.quote_id = kwargs.get("quote_id")
    o.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    o.project_name = kwargs.get("project_name", "测试订单")
    o.status = kwargs.get("status", "pending_confirm")
    o.total_amount = kwargs.get("total_amount", 1000.0)
    o.paid_amount = kwargs.get("paid_amount", 0.0)
    o.unpaid_amount = kwargs.get("unpaid_amount", 1000.0)
    o.cost_amount = kwargs.get("cost_amount", 0.0)
    o.gross_profit = kwargs.get("gross_profit", 0.0)
    o.sales_user_id = kwargs.get("sales_user_id")
    o.delivery_deadline = kwargs.get("delivery_deadline")
    o.installation_address = kwargs.get("installation_address")
    o.remark = kwargs.get("remark")
    o.created_at = kwargs.get("created_at")
    o.items = kwargs.get("items", [])
    o.status_logs = kwargs.get("status_logs", [])
    o.design_tasks = kwargs.get("design_tasks", [])
    o.production_tasks = kwargs.get("production_tasks", [])
    o.installation_tasks = kwargs.get("installation_tasks", [])
    return o


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_orders = AsyncMock(return_value=([], 0))

    async def update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj

    repo.update = AsyncMock(side_effect=update_side_effect)
    repo.create_status_log = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.order_service.OrderRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = OrderService(db)
        svc.repo = mock_repo
        yield svc


# --- List Tests ---

@pytest.mark.asyncio
async def test_list_orders_empty(service, mock_repo):
    mock_repo.list_orders.return_value = ([], 0)
    items, total = await service.list_orders(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_orders_with_results(service, mock_repo):
    o1 = make_mock_order(project_name="订单A")
    o2 = make_mock_order(id=SAMPLE_USER_ID, order_no="O20260629-0002", project_name="订单B")
    mock_repo.list_orders.return_value = ([o1, o2], 2)

    items, total = await service.list_orders(page=1, page_size=20)
    assert total == 2
    assert items[0]["project_name"] == "订单A"
    assert items[1]["project_name"] == "订单B"


# --- Get Tests ---

@pytest.mark.asyncio
async def test_get_order_found(service, mock_repo):
    o = make_mock_order()
    mock_repo.get_by_id.return_value = o
    result = await service.get_order(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["order_no"] == "O20260629-0001"
    assert result["project_name"] == "测试订单"
    assert result["status"] == "pending_confirm"


@pytest.mark.asyncio
async def test_get_order_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.get_order(SAMPLE_ORDER_ID)
    assert result is None


# --- Change Status Tests ---

@pytest.mark.asyncio
async def test_change_status(service, mock_repo):
    o = make_mock_order(status="pending_confirm")
    mock_repo.get_by_id.return_value = o

    result = await service.change_status(SAMPLE_ORDER_ID, "in_production", "开始制作", SAMPLE_USER_ID)
    assert result["status"] == "in_production"
    mock_repo.update.assert_awaited_once()
    mock_repo.create_status_log.assert_awaited_once_with(
        SAMPLE_ORDER_ID, "pending_confirm", "in_production", "开始制作", SAMPLE_USER_ID
    )


@pytest.mark.asyncio
async def test_change_status_order_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="订单不存在"):
        await service.change_status(SAMPLE_ORDER_ID, "cancelled", "取消", SAMPLE_USER_ID)


# --- Set Cost Tests ---

@pytest.mark.asyncio
async def test_set_cost(service, mock_repo):
    o = make_mock_order(total_amount=5000.0)
    mock_repo.get_by_id.return_value = o
    mock_repo.update.return_value = o

    result = await service.set_cost(SAMPLE_ORDER_ID, 3000.0)
    assert result["cost_amount"] == 3000.0
    assert result["gross_profit"] == 2000.0  # 5000 - 3000


@pytest.mark.asyncio
async def test_set_cost_order_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="订单不存在"):
        await service.set_cost(SAMPLE_ORDER_ID, 1000.0)


# --- Auto Calculate Cost Tests ---

@pytest.mark.asyncio
async def test_auto_calculate_cost(service, mock_repo):
    """Auto-calculate sums outsource + material costs."""
    o = make_mock_order(total_amount=10000.0)
    mock_repo.get_by_id.return_value = o

    # Mock db.execute to return outsource sum first, then stock sum
    outsource_result = MagicMock()
    outsource_result.scalar.return_value = 2000.0
    stock_result = MagicMock()
    stock_result.scalar.return_value = 1500.0

    service.db.execute = AsyncMock(side_effect=[outsource_result, stock_result])

    mock_repo.update.return_value = make_mock_order(total_amount=10000.0, cost_amount=3500.0, gross_profit=6500.0)

    result = await service.auto_calculate_cost(SAMPLE_ORDER_ID)
    assert result["cost_amount"] == 3500.0
    assert result["gross_profit"] == 6500.0
