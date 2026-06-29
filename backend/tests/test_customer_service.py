"""Tests for CustomerService: CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.customer_service import CustomerService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_CUSTOMER_ID


def make_mock_customer(**kwargs):
    """Create a mock Customer-like object."""
    now = datetime.now(timezone.utc)
    c = MagicMock()
    c.id = kwargs.get("id", SAMPLE_CUSTOMER_ID)
    c.customer_no = kwargs.get("customer_no", "C20260629-0001")
    c.name = kwargs.get("name", "测试客户")
    c.customer_type = kwargs.get("customer_type", "company")
    c.level = kwargs.get("level", "normal")
    c.phone = kwargs.get("phone", "13800138000")
    c.wechat = kwargs.get("wechat")
    c.address = kwargs.get("address", "北京市朝阳区")
    c.tax_no = kwargs.get("tax_no")
    c.invoice_info = kwargs.get("invoice_info")
    c.default_payment_days = kwargs.get("default_payment_days", 30)
    c.default_discount = kwargs.get("default_discount", 1.0)
    c.remark = kwargs.get("remark")
    c.created_at = kwargs.get("created_at", now)
    c.contacts = kwargs.get("contacts", [])
    return c


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_customers = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.customer_service.CustomerRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        db.refresh = AsyncMock()
        svc = CustomerService(db)
        svc.repo = mock_repo
        yield svc


# --- List Tests ---

@pytest.mark.asyncio
async def test_list_customers_empty(service, mock_repo):
    mock_repo.list_customers.return_value = ([], 0)
    items, total = await service.list_customers(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_customers_with_results(service, mock_repo):
    c1 = make_mock_customer(name="客户A")
    c2 = make_mock_customer(id=SAMPLE_USER_ID, customer_no="C20260629-0002", name="客户B")
    mock_repo.list_customers.return_value = ([c1, c2], 2)

    items, total = await service.list_customers(page=1, page_size=20)
    assert total == 2
    assert items[0]["name"] == "客户A"
    assert items[1]["name"] == "客户B"


# --- Get Tests ---

@pytest.mark.asyncio
async def test_get_customer_found(service, mock_repo):
    c = make_mock_customer()
    mock_repo.get_by_id.return_value = c

    result = await service.get_customer(SAMPLE_CUSTOMER_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_CUSTOMER_ID)
    assert result["customer_no"] == "C20260629-0001"
    assert result["name"] == "测试客户"
    assert result["customer_type"] == "company"
    assert result["level"] == "normal"
    assert result["default_payment_days"] == 30
    assert result["default_discount"] == 1.0


@pytest.mark.asyncio
async def test_get_customer_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.get_customer(SAMPLE_CUSTOMER_ID)
    assert result is None


# --- Create Tests ---

@pytest.mark.asyncio
async def test_create_customer(service, mock_repo):
    async def create_side_effect(data):
        return make_mock_customer(
            customer_no=data.get("customer_no", "C20260629-0002"),
            name=data.get("name", "默认"),
        )

    mock_repo.create.side_effect = create_side_effect

    with patch("app.services.customer_service.generate_customer_no", AsyncMock(return_value="C20260629-0002")):
        result = await service.create_customer({"name": "新客户", "phone": "13900139000"})

    assert result["name"] == "新客户"
    assert result["customer_no"] == "C20260629-0002"


# --- Update Tests ---

@pytest.mark.asyncio
async def test_update_customer(service, mock_repo):
    c = make_mock_customer(name="旧名称")
    mock_repo.get_by_id.return_value = c
    mock_repo.update.return_value = make_mock_customer(name="新名称")

    result = await service.update_customer(SAMPLE_CUSTOMER_ID, {"name": "新名称"})
    assert result["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_customer_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="客户不存在"):
        await service.update_customer(SAMPLE_CUSTOMER_ID, {"name": "新名称"})


# --- Delete Tests ---

@pytest.mark.asyncio
async def test_delete_customer_success(service, mock_repo):
    c = make_mock_customer()
    mock_repo.get_by_id.return_value = c

    result = await service.delete_customer(SAMPLE_CUSTOMER_ID)
    assert result is True
    mock_repo.soft_delete.assert_awaited_once_with(c)


@pytest.mark.asyncio
async def test_delete_customer_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.delete_customer(SAMPLE_CUSTOMER_ID)
    assert result is False


# --- To Response Test ---

def test_to_response_with_contacts(service):
    now = datetime.now(timezone.utc)
    contact = MagicMock()
    contact.id = "contact-1"
    contact.name = "李四"
    contact.phone = "13700137000"
    contact.wechat = "lisi_wx"
    contact.position = "经理"
    contact.is_primary = True
    contact.remark = None

    c = make_mock_customer(contacts=[contact], created_at=now)
    d = service._to_response(c)
    assert d["id"] == str(SAMPLE_CUSTOMER_ID)
    assert len(d["contacts"]) == 1
    assert d["contacts"][0]["name"] == "李四"
    assert d["contacts"][0]["is_primary"] is True
