"""Tests for AerialService: vehicles, personnel, ledgers, expenses, wages, costs."""

import json
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.aerial_service import AerialService, ACTION_CREATE, ACTION_UPDATE
from tests.conftest import SAMPLE_USER_ID


# ── Mock factories ──────────────────────────────────────────────────────────

SAMPLE_VEHICLE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SAMPLE_PERSONNEL_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SAMPLE_LEDGER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
SAMPLE_EXPENSE_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
SAMPLE_WAGE_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
SAMPLE_COST_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def make_mock_vehicle(**kwargs):
    v = MagicMock()
    v.id = kwargs.get("id", SAMPLE_VEHICLE_ID)
    v.plate_number = kwargs.get("plate_number", "京A12345")
    v.vehicle_name = kwargs.get("vehicle_name", "测试高空车")
    v.brand_model = kwargs.get("brand_model", "中联重科")
    v.max_working_height = kwargs.get("max_working_height", 20.0)
    v.platform_capacity = kwargs.get("platform_capacity", 200.0)
    v.purchase_date = kwargs.get("purchase_date", datetime(2024, 1, 1))
    v.status = kwargs.get("status", "active")
    v.default_personnel_id = kwargs.get("default_personnel_id", None)
    v.default_personnel = kwargs.get("default_personnel", None)
    v.insurance_expire_date = kwargs.get("insurance_expire_date", datetime(2026, 12, 31))
    v.inspection_expire_date = kwargs.get("inspection_expire_date", datetime(2026, 6, 30))
    v.maintenance_due_date = kwargs.get("maintenance_due_date", None)
    v.remark = kwargs.get("remark", None)
    v.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    v.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return v


def make_mock_personnel(**kwargs):
    d = MagicMock()
    d.id = kwargs.get("id", SAMPLE_PERSONNEL_ID)
    d.name = kwargs.get("name", "张师傅")
    d.phone = kwargs.get("phone", "13800138000")
    d.license_no = kwargs.get("license_no", "C123456789")
    d.license_type = kwargs.get("license_type", "C1")
    d.license_expire_date = kwargs.get("license_expire_date", datetime(2027, 12, 31))
    d.is_external = kwargs.get("is_external", False)
    d.personnel_type = kwargs.get("personnel_type", "driver")
    d.status = kwargs.get("status", "active")
    d.remark = kwargs.get("remark", None)
    d.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    d.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return d


def make_mock_ledger(**kwargs):
    l = MagicMock()
    l.id = kwargs.get("id", SAMPLE_LEDGER_ID)
    l.ledger_no = kwargs.get("ledger_no", "GT-20260723-001")
    l.work_date = kwargs.get("work_date", datetime(2026, 7, 23))
    l.aerial_vehicle_id = kwargs.get("aerial_vehicle_id", SAMPLE_VEHICLE_ID)
    l.personnel_id = kwargs.get("personnel_id", SAMPLE_PERSONNEL_ID)
    l.work_location = kwargs.get("work_location", "北京朝阳")
    l.customer_name = kwargs.get("customer_name", "测试客户")
    l.work_content = kwargs.get("work_content", "外墙清洗")
    l.receivable_amount = kwargs.get("receivable_amount", 1500.0)
    l.received_amount = kwargs.get("received_amount", 0.0)
    l.final_amount = kwargs.get("final_amount", 1500.0)
    l.payment_status = kwargs.get("payment_status", "pending")
    l.audit_status = kwargs.get("audit_status", "draft")
    l.status = kwargs.get("status", "draft")
    l.work_hours = kwargs.get("work_hours", None)
    l.start_time = kwargs.get("start_time", None)
    l.end_time = kwargs.get("end_time", None)
    l.remark = kwargs.get("remark", None)
    l.void_reason = kwargs.get("void_reason", None)
    l.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    l.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    # Relationships
    l.vehicle = MagicMock()
    l.vehicle.plate_number = "京A12345"
    l.vehicle.brand_model = "中联重科"
    l.personnel = MagicMock()
    l.personnel.name = "张师傅"
    l.personnel.phone = "13800138000"
    l.expenses = []
    l.safety_checks = []
    l.attachments = []
    l.audit_logs = []
    return l


def make_mock_expense(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", SAMPLE_EXPENSE_ID)
    e.ledger_id = kwargs.get("ledger_id", SAMPLE_LEDGER_ID)
    e.personnel_id = kwargs.get("personnel_id", SAMPLE_PERSONNEL_ID)
    e.expense_type = kwargs.get("expense_type", "fuel")
    e.expense_date = kwargs.get("expense_date", datetime(2026, 7, 23))
    e.amount = kwargs.get("amount", 200.0)
    e.remark = kwargs.get("remark", None)
    e.paid_by_personnel = kwargs.get("paid_by_personnel", True)
    e.review_status = kwargs.get("review_status", "pending")
    e.reviewed_by = kwargs.get("reviewed_by", None)
    e.reviewed_at = kwargs.get("reviewed_at", None)
    e.reimbursement_status = kwargs.get("reimbursement_status", "pending")
    e.reimbursed_at = kwargs.get("reimbursed_at", None)
    e.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    # Relationships
    e.ledger = MagicMock()
    e.ledger.ledger_no = "GT-20260723-001"
    e.personnel = MagicMock()
    e.personnel.name = "张师傅"
    return e


def make_mock_wage(**kwargs):
    w = MagicMock()
    w.id = kwargs.get("id", SAMPLE_WAGE_ID)
    w.personnel_id = kwargs.get("personnel_id", SAMPLE_PERSONNEL_ID)
    w.ledger_id = kwargs.get("ledger_id", None)
    w.wage_month = kwargs.get("wage_month", "2026-07")
    w.base_wage = kwargs.get("base_wage", 5000.0)
    w.trip_wage = kwargs.get("trip_wage", 0.0)
    w.hourly_wage = kwargs.get("hourly_wage", 0.0)
    w.commission_amount = kwargs.get("commission_amount", 1000.0)
    w.allowance_amount = kwargs.get("allowance_amount", 0.0)
    w.deduction_amount = kwargs.get("deduction_amount", 0.0)
    w.final_wage_amount = kwargs.get("final_wage_amount", 6000.0)
    w.payment_status = kwargs.get("payment_status", "pending")
    w.paid_at = kwargs.get("paid_at", None)
    w.remark = kwargs.get("remark", None)
    w.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    # Relationships
    w.personnel = MagicMock()
    w.personnel.name = "张师傅"
    return w


def make_mock_cost(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", SAMPLE_COST_ID)
    c.aerial_vehicle_id = kwargs.get("aerial_vehicle_id", SAMPLE_VEHICLE_ID)
    c.cost_type = kwargs.get("cost_type", "fuel")
    c.cost_date = kwargs.get("cost_date", datetime(2026, 7, 23))
    c.amount = kwargs.get("amount", 500.0)
    c.description = kwargs.get("description", "加油")
    c.review_status = kwargs.get("review_status", "pending")
    c.reviewed_by = kwargs.get("reviewed_by", None)
    c.reviewed_at = kwargs.get("reviewed_at", None)
    c.ledger_id = kwargs.get("ledger_id", None)
    c.remark = kwargs.get("remark", None)
    c.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    # Relationships
    c.vehicle = MagicMock()
    c.vehicle.plate_number = "京A12345"
    return c


def make_mock_user(**kwargs):
    u = MagicMock()
    u.id = kwargs.get("id", SAMPLE_USER_ID)
    u.username = kwargs.get("username", "testuser")
    return u


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.list_vehicles = AsyncMock(return_value=([], 0))
    repo.get_vehicle = AsyncMock()
    repo.get_vehicle_by_plate = AsyncMock(return_value=None)
    repo.create_vehicle = AsyncMock()
    repo.update_vehicle = AsyncMock()
    repo.list_personnel = AsyncMock(return_value=([], 0))
    repo.get_personnel = AsyncMock()
    repo.create_personnel = AsyncMock()
    repo.update_personnel = AsyncMock()
    repo.list_ledgers = AsyncMock(return_value=([], 0))
    repo.get_ledger = AsyncMock()
    repo.get_ledger_by_no = AsyncMock(return_value=None)
    repo.get_next_ledger_seq = AsyncMock(return_value=1)
    repo.count_ledgers_today = AsyncMock(return_value=0)
    repo.create_ledger = AsyncMock()
    repo.update_ledger = AsyncMock()
    repo.list_expenses = AsyncMock(return_value=([], 0))
    repo.get_expense = AsyncMock()
    repo.create_expense = AsyncMock()
    repo.update_expense = AsyncMock()
    repo.list_wages = AsyncMock(return_value=([], 0))
    repo.get_wage = AsyncMock()
    repo.create_wage = AsyncMock()
    repo.update_wage = AsyncMock()
    repo.list_costs = AsyncMock(return_value=([], 0))
    repo.get_cost = AsyncMock()
    repo.create_cost = AsyncMock()
    repo.update_cost = AsyncMock()
    repo.list_safety_checks = AsyncMock(return_value=[])
    repo.create_safety_check = AsyncMock()
    repo.list_attachments = AsyncMock(return_value=[])
    repo.create_attachment = AsyncMock()
    repo.delete_attachment = AsyncMock()
    repo.create_audit_log = AsyncMock()
    repo.list_audit_logs = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.aerial_service.AerialRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        user = make_mock_user()
        svc = AerialService(db, user, "127.0.0.1")
        svc.repo = mock_repo
        yield svc


# ── Vehicle tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_vehicles_empty(service, mock_repo):
    mock_repo.list_vehicles.return_value = ([], 0)
    items, total = await service.list_vehicles()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_vehicles(service, mock_repo):
    v = make_mock_vehicle()
    mock_repo.list_vehicles.return_value = ([v], 1)
    items, total = await service.list_vehicles()
    assert total == 1
    assert items[0]["plate_number"] == "京A12345"


@pytest.mark.asyncio
async def test_get_vehicle_found(service, mock_repo):
    v = make_mock_vehicle()
    mock_repo.get_vehicle.return_value = v
    result = await service.get_vehicle(SAMPLE_VEHICLE_ID)
    assert result["plate_number"] == "京A12345"
    assert result["vehicle_name"] == "测试高空车"


@pytest.mark.asyncio
async def test_get_vehicle_not_found(service, mock_repo):
    mock_repo.get_vehicle.return_value = None
    with pytest.raises(ValueError, match="高空车不存在"):
        await service.get_vehicle(SAMPLE_VEHICLE_ID)


@pytest.mark.asyncio
async def test_create_vehicle(service, mock_repo):
    v = make_mock_vehicle()
    mock_repo.create_vehicle.return_value = v
    result = await service.create_vehicle({"plate_number": "京A12345", "vehicle_name": "测试高空车"})
    assert result["plate_number"] == "京A12345"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_create_vehicle_duplicate_plate(service, mock_repo):
    mock_repo.get_vehicle_by_plate.return_value = make_mock_vehicle()
    with pytest.raises(ValueError, match="已存在"):
        await service.create_vehicle({"plate_number": "京A12345"})


@pytest.mark.asyncio
async def test_create_vehicle_empty_plate(service, mock_repo):
    with pytest.raises(ValueError, match="车牌号不能为空"):
        await service.create_vehicle({"plate_number": ""})


@pytest.mark.asyncio
async def test_update_vehicle(service, mock_repo):
    v = make_mock_vehicle()
    mock_repo.get_vehicle.return_value = v

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_vehicle.side_effect = update_side_effect
    result = await service.update_vehicle(SAMPLE_VEHICLE_ID, {"vehicle_name": "新名称"})
    assert result["vehicle_name"] == "新名称"
    mock_repo.create_audit_log.assert_called_once()


# ── Personnel tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_personnel_empty(service, mock_repo):
    mock_repo.list_personnel.return_value = ([], 0)
    items, total = await service.list_personnel()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_personnel_found(service, mock_repo):
    d = make_mock_personnel()
    mock_repo.get_personnel.return_value = d
    result = await service.get_personnel(SAMPLE_PERSONNEL_ID)
    assert result["name"] == "张师傅"


@pytest.mark.asyncio
async def test_get_personnel_not_found(service, mock_repo):
    mock_repo.get_personnel.return_value = None
    with pytest.raises(ValueError, match="人员不存在"):
        await service.get_personnel(SAMPLE_PERSONNEL_ID)


@pytest.mark.asyncio
async def test_create_personnel(service, mock_repo):
    d = make_mock_personnel()
    mock_repo.create_personnel.return_value = d
    result = await service.create_personnel({"name": "张师傅"})
    assert result["name"] == "张师傅"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_create_personnel_empty_name(service, mock_repo):
    with pytest.raises(ValueError, match="姓名不能为空"):
        await service.create_personnel({"name": ""})


@pytest.mark.asyncio
async def test_update_personnel(service, mock_repo):
    d = make_mock_personnel()
    mock_repo.get_personnel.return_value = d

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_personnel.side_effect = update_side_effect
    result = await service.update_personnel(SAMPLE_PERSONNEL_ID, {"name": "李师傅"})
    assert result["name"] == "李师傅"
    mock_repo.create_audit_log.assert_called_once()


# ── Ledger tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_ledgers_empty(service, mock_repo):
    mock_repo.list_ledgers.return_value = ([], 0)
    items, total = await service.list_ledgers()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_ledger_found(service, mock_repo):
    l = make_mock_ledger()
    mock_repo.get_ledger.return_value = l
    result = await service.get_ledger(SAMPLE_LEDGER_ID)
    assert result["ledger_no"] == "GT-20260723-001"
    assert result["receivable_amount"] == 1500.0


@pytest.mark.asyncio
async def test_get_ledger_not_found(service, mock_repo):
    mock_repo.get_ledger.return_value = None
    with pytest.raises(ValueError, match="台账不存在"):
        await service.get_ledger(SAMPLE_LEDGER_ID)


@pytest.mark.asyncio
async def test_create_ledger(service, mock_repo):
    l = make_mock_ledger()
    mock_repo.create_ledger.return_value = l
    result = await service.create_ledger({
        "aerial_vehicle_id": SAMPLE_VEHICLE_ID,
        "personnel_id": SAMPLE_PERSONNEL_ID,
        "work_date": "2026-07-23",
        "work_location": "北京朝阳",
        "customer_name": "测试客户",
        "receivable_amount": 1500.0,
    })
    assert result["ledger_no"] == "GT-20260723-001"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_void_ledger(service, mock_repo):
    l = make_mock_ledger()
    mock_repo.get_ledger.return_value = l

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_ledger.side_effect = update_side_effect
    result = await service.void_ledger(SAMPLE_LEDGER_ID, "测试作废")
    assert result["status"] == "cancelled"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_approve_ledger(service, mock_repo):
    l = make_mock_ledger(audit_status="pending")
    mock_repo.get_ledger.return_value = l

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_ledger.side_effect = update_side_effect
    result = await service.approve_ledger(SAMPLE_LEDGER_ID, "审核通过")
    assert result["audit_status"] == "approved"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_reject_ledger(service, mock_repo):
    l = make_mock_ledger(audit_status="pending")
    mock_repo.get_ledger.return_value = l

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_ledger.side_effect = update_side_effect
    result = await service.reject_ledger(SAMPLE_LEDGER_ID, "信息不完整")
    assert result["audit_status"] == "rejected"
    mock_repo.create_audit_log.assert_called_once()


# ── Expense tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_expenses_empty(service, mock_repo):
    mock_repo.list_expenses.return_value = ([], 0)
    items, total = await service.list_expenses()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_expense(service, mock_repo):
    e = make_mock_expense()
    mock_repo.get_ledger.return_value = make_mock_ledger()
    mock_repo.get_personnel.return_value = make_mock_personnel()
    mock_repo.create_expense.return_value = e
    result = await service.create_expense({
        "ledger_id": SAMPLE_LEDGER_ID,
        "personnel_id": SAMPLE_PERSONNEL_ID,
        "expense_type": "fuel",
        "amount": 200.0,
        "expense_date": "2026-07-23",
    })
    assert result["expense_type"] == "fuel"
    assert result["amount"] == 200.0


@pytest.mark.asyncio
async def test_review_expense_approve(service, mock_repo):
    e = make_mock_expense(review_status="pending")
    mock_repo.get_expense.return_value = e

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_expense.side_effect = update_side_effect
    service._sum_expenses_for_ledger = AsyncMock(return_value=150.0)
    result = await service.review_expense(SAMPLE_EXPENSE_ID, "approved", "审核通过")
    assert result["review_status"] == "approved"
    mock_repo.create_audit_log.assert_called_once()


@pytest.mark.asyncio
async def test_reimburse_expense(service, mock_repo):
    e = make_mock_expense(review_status="approved", reimbursement_status="pending_reimbursement")
    mock_repo.get_expense.return_value = e

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_expense.side_effect = update_side_effect
    result = await service.reimburse_expense(SAMPLE_EXPENSE_ID, "已报销")
    assert result["reimbursement_status"] == "reimbursed"
    mock_repo.create_audit_log.assert_called_once()


# ── Wage tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_wages_empty(service, mock_repo):
    mock_repo.list_wages.return_value = ([], 0)
    items, total = await service.list_wages()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_wage(service, mock_repo):
    w = make_mock_wage()
    mock_repo.get_personnel.return_value = make_mock_personnel()
    mock_repo.create_wage.return_value = w
    result = await service.create_wage({
        "personnel_id": SAMPLE_PERSONNEL_ID,
        "wage_month": "2026-07",
        "base_wage": 5000.0,
        "commission_amount": 1000.0,
    })
    assert result["final_wage_amount"] == 6000.0


@pytest.mark.asyncio
async def test_pay_wage(service, mock_repo):
    w = make_mock_wage(payment_status="pending", ledger_id=SAMPLE_LEDGER_ID)
    mock_repo.get_wage.return_value = w

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_wage.side_effect = update_side_effect
    result = await service.pay_wage(SAMPLE_WAGE_ID, "已发放")
    assert result["payment_status"] == "paid"
    mock_repo.create_audit_log.assert_called_once()


# ── Cost tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_costs_empty(service, mock_repo):
    mock_repo.list_costs.return_value = ([], 0)
    items, total = await service.list_costs()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_cost(service, mock_repo):
    c = make_mock_cost()
    mock_repo.get_vehicle.return_value = make_mock_vehicle()
    mock_repo.create_cost.return_value = c
    result = await service.create_cost({
        "aerial_vehicle_id": SAMPLE_VEHICLE_ID,
        "cost_type": "fuel",
        "amount": 500.0,
        "cost_date": "2026-07-23",
    })
    assert result["cost_type"] == "fuel"
    assert result["amount"] == 500.0


@pytest.mark.asyncio
async def test_review_cost(service, mock_repo):
    c = make_mock_cost(review_status="pending")
    mock_repo.get_cost.return_value = c

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    mock_repo.update_cost.side_effect = update_side_effect
    result = await service.review_cost(SAMPLE_COST_ID, "approved", "审核通过")
    assert result["review_status"] == "approved"
