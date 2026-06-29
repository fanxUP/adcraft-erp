"""Tests for OutsourceService: vendor/task/payment CRUD."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.outsource_service import OutsourceService
from tests.conftest import SAMPLE_USER_ID, SAMPLE_ORDER_ID


def make_mock_vendor(**kwargs):
    v = MagicMock()
    v.id = kwargs.get("id", SAMPLE_USER_ID)
    v.vendor_no = kwargs.get("vendor_no", "V20260629-0001")
    v.name = kwargs.get("name", "测试外协商")
    v.contact_person = kwargs.get("contact_person", "王经理")
    v.phone = kwargs.get("phone", "13900139000")
    v.address = kwargs.get("address", "深圳市宝安区")
    v.service_type = kwargs.get("service_type", "加工")
    v.coop_rating = kwargs.get("coop_rating", "A")
    v.remark = kwargs.get("remark")
    v.is_active = kwargs.get("is_active", True)
    v.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return v


def make_mock_outsource_task(**kwargs):
    t = MagicMock()
    t.id = kwargs.get("id", SAMPLE_ORDER_ID)
    t.task_no = kwargs.get("task_no", "OT20260629-0001")
    t.vendor_id = kwargs.get("vendor_id", SAMPLE_USER_ID)
    t.order_id = kwargs.get("order_id", SAMPLE_ORDER_ID)
    t.task_type = kwargs.get("task_type", "laser_cutting")
    t.description = kwargs.get("description", "激光切割")
    t.quantity = kwargs.get("quantity", 10.0)
    t.unit_price = kwargs.get("unit_price", 50.0)
    t.total_amount = kwargs.get("total_amount", 500.0)
    t.status = kwargs.get("status", "pending")
    t.expected_at = kwargs.get("expected_at")
    t.completed_at = kwargs.get("completed_at")
    t.remark = kwargs.get("remark")
    t.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return t


def make_mock_outsource_payment(**kwargs):
    p = MagicMock()
    p.id = kwargs.get("id", SAMPLE_USER_ID)
    p.payment_no = kwargs.get("payment_no", "OP20260629-0001")
    p.vendor_id = kwargs.get("vendor_id", SAMPLE_USER_ID)
    p.task_id = kwargs.get("task_id", SAMPLE_ORDER_ID)
    p.amount = kwargs.get("amount", 500.0)
    p.payment_method = kwargs.get("payment_method", "bank_transfer")
    p.paid_at = kwargs.get("paid_at", datetime.now(timezone.utc))
    p.remark = kwargs.get("remark")
    p.created_by = kwargs.get("created_by", SAMPLE_USER_ID)
    p.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return p


@pytest.fixture
def mock_repos():
    vendor_repo = MagicMock()
    vendor_repo.get_by_id = AsyncMock()
    vendor_repo.list_vendors = AsyncMock(return_value=([], 0))
    vendor_repo.create = AsyncMock()
    vendor_repo.update = AsyncMock()
    vendor_repo.soft_delete = AsyncMock()

    async def vendor_update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj
    vendor_repo.update.side_effect = vendor_update_side_effect

    task_repo = MagicMock()
    task_repo.get_by_id = AsyncMock()
    task_repo.list_tasks = AsyncMock(return_value=([], 0))
    task_repo.create = AsyncMock()

    async def task_update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj
    task_repo.update.side_effect = task_update_side_effect

    payment_repo = MagicMock()
    payment_repo.list_payments = AsyncMock(return_value=([], 0))
    payment_repo.create = AsyncMock()

    return vendor_repo, task_repo, payment_repo


@pytest.fixture
def service(mock_repos):
    vendor_repo, task_repo, payment_repo = mock_repos
    with patch("app.services.outsource_service.OutsourceVendorRepository") as MockVendorRepo, \
         patch("app.services.outsource_service.OutsourceTaskRepository") as MockTaskRepo, \
         patch("app.services.outsource_service.OutsourcePaymentRepository") as MockPaymentRepo:
        MockVendorRepo.return_value = vendor_repo
        MockTaskRepo.return_value = task_repo
        MockPaymentRepo.return_value = payment_repo
        db = AsyncMock()
        # Mock _vendor_name lookup
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "测试外协商"
        db.execute = AsyncMock(return_value=name_result)

        svc = OutsourceService(db)
        svc.vendor_repo = vendor_repo
        svc.task_repo = task_repo
        svc.payment_repo = payment_repo
        yield svc, vendor_repo, task_repo, payment_repo


# ════════════════════════════════════════════════
# Vendor Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_vendors_empty(service):
    svc, vr, _, _ = service
    vr.list_vendors.return_value = ([], 0)
    items, total = await svc.list_vendors(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_vendor_found(service):
    svc, vr, _, _ = service
    v = make_mock_vendor()
    vr.get_by_id.return_value = v
    result = await svc.get_vendor(SAMPLE_USER_ID)
    assert result is not None
    assert result["name"] == "测试外协商"
    assert result["vendor_no"] == "V20260629-0001"


@pytest.mark.asyncio
async def test_get_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    result = await svc.get_vendor(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_vendor(service):
    svc, vr, _, _ = service
    vr.create.return_value = make_mock_vendor(name="新外协商")
    with patch("app.services.outsource_service.generate_vendor_no", AsyncMock(return_value="V20260629-0002")):
        result = await svc.create_vendor({"name": "新外协商"})
    assert result["name"] == "新外协商"


@pytest.mark.asyncio
async def test_update_vendor(service):
    svc, vr, _, _ = service
    v = make_mock_vendor(name="旧名称")
    vr.get_by_id.return_value = v
    result = await svc.update_vendor(SAMPLE_USER_ID, {"name": "新名称"})
    assert result["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    with pytest.raises(ValueError, match="外协商不存在"):
        await svc.update_vendor(SAMPLE_USER_ID, {"name": "新名称"})


@pytest.mark.asyncio
async def test_delete_vendor_success(service):
    svc, vr, _, _ = service
    v = make_mock_vendor()
    vr.get_by_id.return_value = v
    result = await svc.delete_vendor(SAMPLE_USER_ID)
    assert result is True
    vr.soft_delete.assert_awaited_once_with(v)


@pytest.mark.asyncio
async def test_delete_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    result = await svc.delete_vendor(SAMPLE_USER_ID)
    assert result is False


# ════════════════════════════════════════════════
# Task Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_tasks_empty(service):
    svc, _, tr, _ = service
    tr.list_tasks.return_value = ([], 0)
    items, total = await svc.list_tasks(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_task_found(service):
    svc, _, tr, _ = service
    t = make_mock_outsource_task()
    tr.get_by_id.return_value = t
    result = await svc.get_task(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["task_no"] == "OT20260629-0001"


@pytest.mark.asyncio
async def test_get_task_not_found(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = None
    result = await svc.get_task(SAMPLE_ORDER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_task(service):
    svc, _, tr, _ = service
    tr.create.return_value = make_mock_outsource_task(
        task_no="OT20260629-0002", quantity=5, unit_price=100.0, total_amount=500.0
    )
    with patch("app.services.outsource_service.generate_outsource_task_no", AsyncMock(return_value="OT20260629-0002")):
        result = await svc.create_task({
            "vendor_id": SAMPLE_USER_ID,
            "order_id": SAMPLE_ORDER_ID,
            "task_type": "laser_cutting",
            "quantity": 5,
            "unit_price": 100.0,
        })
    assert result["task_no"] == "OT20260629-0002"


@pytest.mark.asyncio
async def test_update_task_with_unit_price_change(service):
    svc, _, tr, _ = service
    t = make_mock_outsource_task(quantity=10, unit_price=50.0, total_amount=500.0)
    tr.get_by_id.return_value = t

    result = await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 60.0})
    # total_amount should be recalculated: 10 * 60 = 600
    assert result["total_amount"] == 600.0


@pytest.mark.asyncio
async def test_update_task_not_found(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = None
    with pytest.raises(ValueError, match="外协任务不存在"):
        await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 60.0})


# ════════════════════════════════════════════════
# Payment Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_payments_empty(service):
    svc, _, _, pr = service
    pr.list_payments.return_value = ([], 0)
    items, total = await svc.list_payments(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_payment(service):
    svc, _, _, pr = service
    pr.create.return_value = make_mock_outsource_payment(payment_no="OP20260629-0002")
    with patch("app.services.outsource_service.generate_outsource_payment_no", AsyncMock(return_value="OP20260629-0002")):
        result = await svc.create_payment({
            "vendor_id": SAMPLE_USER_ID,
            "amount": 500.0,
        })
    assert result["payment_no"] == "OP20260629-0002"
