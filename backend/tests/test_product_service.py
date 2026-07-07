"""Tests for ProductService: product/material/process CRUD."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.product_service import ProductService
from tests.conftest import SAMPLE_USER_ID


def make_mock_category(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", SAMPLE_USER_ID)
    c.name = kwargs.get("name", "测试分类")
    c.parent_id = kwargs.get("parent_id")
    c.sort_order = kwargs.get("sort_order", 0)
    return c


def make_mock_product(**kwargs):
    p = MagicMock()
    p.id = kwargs.get("id", SAMPLE_USER_ID)
    p.category_id = kwargs.get("category_id")
    p.name = kwargs.get("name", "测试产品")
    p.unit = kwargs.get("unit", "平方米")
    p.pricing_method = kwargs.get("pricing_method", "by_area")
    p.default_price = kwargs.get("default_price", 100.0)
    p.min_charge = kwargs.get("min_charge", 50.0)
    p.remark = kwargs.get("remark")
    p.is_active = kwargs.get("is_active", True)
    p.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return p


def make_mock_material(**kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", SAMPLE_USER_ID)
    m.name = kwargs.get("name", "测试材质")
    m.spec = kwargs.get("spec", "1.0mm")
    m.unit = kwargs.get("unit", "平方米")
    m.purchase_price = kwargs.get("purchase_price", 50.0)
    m.sale_price = kwargs.get("sale_price", 80.0)
    m.loss_rate = kwargs.get("loss_rate", 0.05)
    m.safe_stock = kwargs.get("safe_stock", 100.0)
    m.remark = kwargs.get("remark")
    m.is_active = kwargs.get("is_active", True)
    m.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return m


def make_mock_process(**kwargs):
    pr = MagicMock()
    pr.id = kwargs.get("id", SAMPLE_USER_ID)
    pr.name = kwargs.get("name", "测试工艺")
    pr.charge_method = kwargs.get("charge_method", "by_unit")
    pr.default_price = kwargs.get("default_price", 30.0)
    pr.remark = kwargs.get("remark")
    pr.is_active = kwargs.get("is_active", True)
    pr.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return pr


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    # Categories
    repo.list_categories = AsyncMock(return_value=[])
    repo.create_category = AsyncMock()
    repo.delete_category = AsyncMock(return_value=True)
    # Products
    repo.get_product_by_id = AsyncMock()
    repo.list_products = AsyncMock(return_value=([], 0))
    repo.create_product = AsyncMock()
    repo.update_product = AsyncMock()
    repo.delete_product = AsyncMock()
    # Materials
    repo.get_material_by_id = AsyncMock()
    repo.list_materials = AsyncMock(return_value=([], 0))
    repo.create_material = AsyncMock()
    repo.update_material = AsyncMock()
    repo.delete_material = AsyncMock()
    # Processes
    repo.get_process_by_id = AsyncMock()
    repo.list_processes = AsyncMock(return_value=([], 0))
    repo.create_process = AsyncMock()
    repo.update_process = AsyncMock()
    repo.delete_process = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.product_service.ProductRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = ProductService(db)
        svc.repo = mock_repo
        yield svc


# ── Categories ──

@pytest.mark.asyncio
async def test_list_categories(service, mock_repo):
    c1 = make_mock_category(name="发光字")
    c2 = make_mock_category(id=SAMPLE_USER_ID, name="不发光字")
    mock_repo.list_categories.return_value = [c1, c2]

    result = await service.list_categories()
    assert len(result) == 2
    assert result[0]["name"] == "发光字"
    assert result[1]["name"] == "不发光字"


@pytest.mark.asyncio
async def test_create_category(service, mock_repo):
    mock_repo.create_category.return_value = make_mock_category(name="新分类")
    result = await service.create_category({"name": "新分类"})
    assert result["name"] == "新分类"


@pytest.mark.asyncio
async def test_delete_category(service, mock_repo):
    result = await service.delete_category(SAMPLE_USER_ID)
    assert result is True
    mock_repo.delete_category.assert_awaited_once_with(SAMPLE_USER_ID)


# ── Products ──

@pytest.mark.asyncio
async def test_list_products_empty(service, mock_repo):
    mock_repo.list_products.return_value = ([], 0)
    items, total = await service.list_products(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_products_with_results(service, mock_repo):
    p1 = make_mock_product(name="产品A")
    p2 = make_mock_product(name="产品B")
    mock_repo.list_products.return_value = ([p1, p2], 2)

    items, total = await service.list_products(page=1, page_size=20)
    assert total == 2
    assert items[0]["name"] == "产品A"
    assert items[1]["name"] == "产品B"


@pytest.mark.asyncio
async def test_get_product_found(service, mock_repo):
    p = make_mock_product()
    mock_repo.get_product_by_id.return_value = p

    result = await service.get_product(SAMPLE_USER_ID)
    assert result is not None
    assert result["name"] == "测试产品"
    assert result["default_price"] == 100.0


@pytest.mark.asyncio
async def test_get_product_not_found(service, mock_repo):
    mock_repo.get_product_by_id.return_value = None
    result = await service.get_product(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_product(service, mock_repo):
    mock_repo.create_product.return_value = make_mock_product(name="新产品")
    result = await service.create_product({"name": "新产品"})
    assert result["name"] == "新产品"


@pytest.mark.asyncio
async def test_update_product(service, mock_repo):
    p = make_mock_product(name="旧名称")
    mock_repo.get_product_by_id.return_value = p
    mock_repo.update_product.return_value = make_mock_product(name="新名称")

    result = await service.update_product(SAMPLE_USER_ID, {"name": "新名称"})
    assert result["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_product_not_found(service, mock_repo):
    mock_repo.get_product_by_id.return_value = None
    with pytest.raises(ValueError, match="产品不存在"):
        await service.update_product(SAMPLE_USER_ID, {"name": "新名称"})


@pytest.mark.asyncio
async def test_delete_product_success(service, mock_repo):
    p = make_mock_product()
    mock_repo.get_product_by_id.return_value = p
    result = await service.delete_product(SAMPLE_USER_ID)
    assert result is True
    
@pytest.mark.asyncio
async def test_delete_product_not_found(service, mock_repo):
    mock_repo.get_product_by_id.return_value = None
    result = await service.delete_product(SAMPLE_USER_ID)
    assert result is False


# ── Materials ──

@pytest.mark.asyncio
async def test_list_materials_empty(service, mock_repo):
    mock_repo.list_materials.return_value = ([], 0)
    items, total = await service.list_materials(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_material_found(service, mock_repo):
    m = make_mock_material()
    mock_repo.get_material_by_id.return_value = m
    result = await service.get_material(SAMPLE_USER_ID)
    assert result is not None
    assert result["name"] == "测试材质"
    assert result["purchase_price"] == 50.0
    assert result["sale_price"] == 80.0
    assert result["loss_rate"] == 0.05


@pytest.mark.asyncio
async def test_get_material_not_found(service, mock_repo):
    mock_repo.get_material_by_id.return_value = None
    result = await service.get_material(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_material(service, mock_repo):
    mock_repo.create_material.return_value = make_mock_material(name="新材质")
    result = await service.create_material({"name": "新材质"})
    assert result["name"] == "新材质"


@pytest.mark.asyncio
async def test_update_material(service, mock_repo):
    m = make_mock_material(name="旧材质")
    mock_repo.get_material_by_id.return_value = m
    mock_repo.update_material.return_value = make_mock_material(name="新材质")

    result = await service.update_material(SAMPLE_USER_ID, {"name": "新材质"})
    assert result["name"] == "新材质"


@pytest.mark.asyncio
async def test_update_material_not_found(service, mock_repo):
    mock_repo.get_material_by_id.return_value = None
    with pytest.raises(ValueError, match="材质不存在"):
        await service.update_material(SAMPLE_USER_ID, {"name": "新材质"})


@pytest.mark.asyncio
async def test_delete_material_success(service, mock_repo):
    m = make_mock_material()
    mock_repo.get_material_by_id.return_value = m
    result = await service.delete_material(SAMPLE_USER_ID)
    assert result is True

@pytest.mark.asyncio
async def test_delete_material_not_found(service, mock_repo):
    mock_repo.get_material_by_id.return_value = None
    result = await service.delete_material(SAMPLE_USER_ID)
    assert result is False


# ── Processes ──

@pytest.mark.asyncio
async def test_list_processes_empty(service, mock_repo):
    mock_repo.list_processes.return_value = ([], 0)
    items, total = await service.list_processes(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_process_found(service, mock_repo):
    pr = make_mock_process()
    mock_repo.get_process_by_id.return_value = pr
    result = await service.get_process(SAMPLE_USER_ID)
    assert result is not None
    assert result["name"] == "测试工艺"
    assert result["default_price"] == 30.0


@pytest.mark.asyncio
async def test_get_process_not_found(service, mock_repo):
    mock_repo.get_process_by_id.return_value = None
    result = await service.get_process(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_process(service, mock_repo):
    mock_repo.create_process.return_value = make_mock_process(name="新工艺")
    result = await service.create_process({"name": "新工艺"})
    assert result["name"] == "新工艺"


@pytest.mark.asyncio
async def test_update_process(service, mock_repo):
    pr = make_mock_process(name="旧工艺")
    mock_repo.get_process_by_id.return_value = pr
    mock_repo.update_process.return_value = make_mock_process(name="新工艺")

    result = await service.update_process(SAMPLE_USER_ID, {"name": "新工艺"})
    assert result["name"] == "新工艺"


@pytest.mark.asyncio
async def test_update_process_not_found(service, mock_repo):
    mock_repo.get_process_by_id.return_value = None
    with pytest.raises(ValueError, match="工艺不存在"):
        await service.update_process(SAMPLE_USER_ID, {"name": "新工艺"})


@pytest.mark.asyncio
async def test_delete_process_success(service, mock_repo):
    pr = make_mock_process()
    mock_repo.get_process_by_id.return_value = pr
    result = await service.delete_process(SAMPLE_USER_ID)
    assert result is True

@pytest.mark.asyncio
async def test_delete_process_not_found(service, mock_repo):
    mock_repo.get_process_by_id.return_value = None
    result = await service.delete_process(SAMPLE_USER_ID)
    assert result is False
