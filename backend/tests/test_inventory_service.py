"""Tests for InventoryService: CRUD, stock_in, stock_out."""

from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.inventory_service import InventoryService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_ORDER_ID


def make_mock_item(**kwargs):
    i = MagicMock()
    i.id = kwargs.get("id", SAMPLE_USER_ID)
    i.material_name = kwargs.get("material_name", "PVC板")
    i.material_unit = kwargs.get("material_unit", "张")
    i.category = kwargs.get("category", "板材")
    i.spec = kwargs.get("spec", "1.22×2.44m")
    i.quantity = kwargs.get("quantity", 50.0)
    i.min_quantity = kwargs.get("min_quantity", 10.0)
    i.unit_cost = kwargs.get("unit_cost", 100.0)
    i.remark = kwargs.get("remark")
    i.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return i


def make_mock_record(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", SAMPLE_ORDER_ID)
    r.item_id = kwargs.get("item_id", SAMPLE_USER_ID)
    r.record_type = kwargs.get("record_type", "in")
    r.quantity = kwargs.get("quantity", 10.0)
    r.unit_cost = kwargs.get("unit_cost", 100.0)
    r.total_cost = kwargs.get("total_cost", 1000.0)
    r.order_id = kwargs.get("order_id", SAMPLE_ORDER_ID)
    r.remark = kwargs.get("remark")
    r.operated_at = kwargs.get("operated_at", datetime.now(timezone.utc))
    r.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return r


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_items = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    repo.update = AsyncMock()

    async def update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj

    repo.update.side_effect = update_side_effect
    repo.list_records = AsyncMock(return_value=([], 0))
    repo.create_record = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.inventory_service.InventoryRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        # Mock _item_name lookup
        db.execute = AsyncMock()
        svc = InventoryService(db)
        svc.repo = mock_repo
        yield svc


# --- Item CRUD ---

@pytest.mark.asyncio
async def test_list_items_empty(service, mock_repo):
    mock_repo.list_items.return_value = ([], 0)
    items, total = await service.list_items(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_item_found(service, mock_repo):
    i = make_mock_item()
    mock_repo.get_by_id.return_value = i
    result = await service.get_item(SAMPLE_USER_ID)
    assert result is not None
    assert result["material_name"] == "PVC板"
    assert result["quantity"] == 50.0
    assert result["unit_cost"] == 100.0


@pytest.mark.asyncio
async def test_get_item_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.get_item(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_item(service, mock_repo):
    mock_repo.create.return_value = make_mock_item(material_name="新物料")
    result = await service.create_item({"material_name": "新物料"})
    assert result["material_name"] == "新物料"


@pytest.mark.asyncio
async def test_update_item(service, mock_repo):
    i = make_mock_item(material_name="旧名称")
    mock_repo.get_by_id.return_value = i

    result = await service.update_item(SAMPLE_USER_ID, {"material_name": "新名称"})
    assert result["material_name"] == "新名称"


@pytest.mark.asyncio
async def test_update_item_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="库存物料不存在"):
        await service.update_item(SAMPLE_USER_ID, {"material_name": "新名称"})


# --- Stock Records ---

@pytest.mark.asyncio
async def test_list_records_empty(service, mock_repo):
    mock_repo.list_records.return_value = ([], 0)
    # Mock _item_name
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = "PVC板"
    service.db.execute = AsyncMock(return_value=result_mock)

    items, total = await service.list_records(page=1, page_size=20)
    assert items == []
    assert total == 0


# --- Stock In ---

@pytest.mark.asyncio
async def test_stock_in(service, mock_repo):
    """Stock in increases item quantity and creates a record."""
    item = make_mock_item(quantity=50.0, unit_cost=80.0)
    mock_repo.get_by_id.return_value = item
    mock_repo.create_record.return_value = make_mock_record(
        record_type="in", quantity=10.0, unit_cost=100.0, total_cost=1000.0
    )

    # Mock _item_name
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = "PVC板"
    service.db.execute = AsyncMock(return_value=result_mock)

    result = await service.stock_in({
        "item_id": str(SAMPLE_USER_ID),
        "quantity": 10.0,
        "unit_cost": 100.0,
    })

    assert result["record_type"] == "in"
    assert result["quantity"] == 10.0
    # Item quantity should have increased
    assert item.quantity == 60.0  # 50 + 10
    assert item.unit_cost == 100.0  # updated to latest


# --- Stock Out ---

@pytest.mark.asyncio
async def test_stock_out(service, mock_repo):
    """Stock out deducts quantity and creates a record."""
    item = make_mock_item(quantity=50.0, unit_cost=80.0)
    mock_repo.get_by_id.return_value = item
    mock_repo.create_record.return_value = make_mock_record(
        record_type="out", quantity=5.0, unit_cost=80.0, total_cost=400.0
    )

    # Mock _item_name
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = "PVC板"
    service.db.execute = AsyncMock(return_value=result_mock)

    result = await service.stock_out({
        "item_id": str(SAMPLE_USER_ID),
        "quantity": 5.0,
        "order_id": str(SAMPLE_ORDER_ID),
    })

    assert result["record_type"] == "out"
    assert result["quantity"] == 5.0
    assert item.quantity == 45.0  # 50 - 5


@pytest.mark.asyncio
async def test_stock_out_insufficient(service, mock_repo):
    """Stock out raises error when quantity exceeds available stock."""
    item = make_mock_item(quantity=5.0)
    mock_repo.get_by_id.return_value = item

    with pytest.raises(ValueError, match="库存不足"):
        await service.stock_out({
            "item_id": str(SAMPLE_USER_ID),
            "quantity": 10.0,
        })


@pytest.mark.asyncio
async def test_stock_out_item_not_found(service, mock_repo):
    """Stock out raises error when item does not exist."""
    mock_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="库存物料不存在"):
        await service.stock_out({
            "item_id": str(SAMPLE_USER_ID),
            "quantity": 5.0,
        })
