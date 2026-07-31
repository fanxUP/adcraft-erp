"""Tests for EmployeeService (employees 模块，mock repo 模式)."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.employee_service import EmployeeService

SAMPLE_EMPLOYEE_ID = "11111111-1111-1111-1111-111111111111"


def make_mock_employee(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", SAMPLE_EMPLOYEE_ID)
    e.employee_no = kwargs.get("employee_no", "EMP001")
    e.name = kwargs.get("name", "王小明")
    e.phone = kwargs.get("phone", "13800138000")
    e.gender = kwargs.get("gender", "male")
    e.ethnicity = kwargs.get("ethnicity", "汉族")
    e.birth_date = kwargs.get("birth_date", date(1990, 1, 1))
    e.department = kwargs.get("department", "production")
    e.position = kwargs.get("position", "技术员")
    e.employment_type = kwargs.get("employment_type", "full_time")
    e.employment_status = kwargs.get("employment_status", "active")
    e.hire_date = kwargs.get("hire_date", date(2024, 3, 1))
    e.resignation_date = kwargs.get("resignation_date", None)
    e.id_card = kwargs.get("id_card", "110101199001011234")
    e.license_no = kwargs.get("license_no", "C123456789")
    e.license_type = kwargs.get("license_type", "C1")
    e.license_expire_date = kwargs.get("license_expire_date", datetime(2027, 6, 30, 0, 0))
    e.id_card_front_url = kwargs.get("id_card_front_url", "/uploads/202607/front.png")
    e.id_card_back_url = kwargs.get("id_card_back_url", "/uploads/202607/back.png")
    e.education = kwargs.get("education", "college")
    e.emergency_contact = kwargs.get("emergency_contact", None)
    e.emergency_phone = kwargs.get("emergency_phone", None)
    e.skills = kwargs.get("skills", [])
    e.base_salary = kwargs.get("base_salary", 5000.0)
    e.bank_name = kwargs.get("bank_name", "工商银行")
    e.bank_account = kwargs.get("bank_account", "6222021234567890")
    e.address = kwargs.get("address", None)
    e.user_id = kwargs.get("user_id", None)
    e.remark = kwargs.get("remark", None)
    e.is_active = kwargs.get("is_active", True)
    e.created_at = kwargs.get("created_at", datetime(2026, 7, 31, 9, 0))
    return e


@pytest.fixture
def service():
    repo = MagicMock()
    repo.list = AsyncMock(return_value=([], 0))
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    with patch("app.services.employee_service.EmployeeRepository") as MockRepoClass:
        MockRepoClass.return_value = repo
        svc = EmployeeService(AsyncMock())
        svc.repo = repo
        yield svc


# ── list / get ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_employees_includes_ethnicity(service):
    service.repo.list.return_value = ([make_mock_employee()], 1)
    items, total = await service.list_employees()
    assert total == 1
    assert items[0]["gender"] == "male"
    assert items[0]["ethnicity"] == "汉族"


@pytest.mark.asyncio
async def test_get_employee_returns_ethnicity(service):
    service.repo.get_by_id.return_value = make_mock_employee()
    result = await service.get_employee(SAMPLE_EMPLOYEE_ID)
    assert result["gender"] == "male"
    assert result["ethnicity"] == "汉族"


# ── create ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_employee_passes_ethnicity(service):
    service.repo.create.return_value = make_mock_employee(ethnicity="维吾尔族")
    with patch("app.services.employee_service.generate_employee_no", new=AsyncMock(return_value="EMP100")):
        result = await service.create_employee({"name": "王小明", "ethnicity": "维吾尔族"})
    assert result["ethnicity"] == "维吾尔族"
    args, _ = service.repo.create.call_args
    assert args[0]["ethnicity"] == "维吾尔族"


@pytest.mark.asyncio
async def test_create_employee_auto_generates_employee_no(service):
    service.repo.create.return_value = make_mock_employee(employee_no="EMP100")
    with patch("app.services.employee_service.generate_employee_no", new=AsyncMock(return_value="EMP100")) as gen:
        await service.create_employee({"name": "王小明"})
        gen.assert_awaited_once()
    args, _ = service.repo.create.call_args
    assert args[0]["employee_no"] == "EMP100"


# ── update ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_employee_sets_ethnicity(service):
    e = make_mock_employee()
    service.repo.get_by_id.return_value = e

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    service.repo.update.side_effect = update_side_effect
    result = await service.update_employee(SAMPLE_EMPLOYEE_ID, {"ethnicity": "哈萨克族"})
    assert result["ethnicity"] == "哈萨克族"


@pytest.mark.asyncio
async def test_update_employee_not_found(service):
    service.repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="员工不存在"):
        await service.update_employee(SAMPLE_EMPLOYEE_ID, {"ethnicity": "回族"})


# ── 驾驶证 + 身份证正反面 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_employee_includes_license_idcard(service):
    service.repo.list.return_value = ([make_mock_employee()], 1)
    items, total = await service.list_employees()
    assert total == 1
    assert items[0]["license_no"] == "C123456789"
    assert items[0]["license_type"] == "C1"
    assert items[0]["license_expire_date"] == "2027-06-30T00:00:00"
    assert items[0]["id_card_front_url"] == "/uploads/202607/front.png"
    assert items[0]["id_card_back_url"] == "/uploads/202607/back.png"


@pytest.mark.asyncio
async def test_get_employee_returns_license_idcard(service):
    service.repo.get_by_id.return_value = make_mock_employee()
    result = await service.get_employee(SAMPLE_EMPLOYEE_ID)
    assert result["license_no"] == "C123456789"
    assert result["id_card_front_url"] == "/uploads/202607/front.png"
    assert result["id_card_back_url"] == "/uploads/202607/back.png"


@pytest.mark.asyncio
async def test_create_employee_passes_license_idcard(service):
    service.repo.create.return_value = make_mock_employee(license_no="B222222222", license_type="B2",
                                                          id_card_front_url="/uploads/202607/a.png",
                                                          id_card_back_url="/uploads/202607/b.png")
    with patch("app.services.employee_service.generate_employee_no", new=AsyncMock(return_value="EMP100")):
        result = await service.create_employee({"name": "王小明", "license_no": "B222222222",
                                                "license_type": "B2", "id_card_front_url": "/uploads/202607/a.png",
                                                "id_card_back_url": "/uploads/202607/b.png"})
    assert result["license_no"] == "B222222222"
    assert result["license_type"] == "B2"
    assert result["id_card_front_url"] == "/uploads/202607/a.png"
    assert result["id_card_back_url"] == "/uploads/202607/b.png"
    args, _ = service.repo.create.call_args
    assert args[0]["license_no"] == "B222222222"
    assert args[0]["id_card_back_url"] == "/uploads/202607/b.png"


@pytest.mark.asyncio
async def test_create_employee_converts_license_expire_date(service):
    service.repo.create.return_value = make_mock_employee()
    with patch("app.services.employee_service.generate_employee_no", new=AsyncMock(return_value="EMP100")):
        await service.create_employee({"name": "王小明", "license_expire_date": "2027-06-30T00:00:00"})
    args, _ = service.repo.create.call_args
    assert args[0]["license_expire_date"] == datetime(2027, 6, 30, 0, 0)


@pytest.mark.asyncio
async def test_create_employee_license_expire_date_empty_becomes_none(service):
    service.repo.create.return_value = make_mock_employee()
    with patch("app.services.employee_service.generate_employee_no", new=AsyncMock(return_value="EMP100")):
        await service.create_employee({"name": "王小明", "license_expire_date": ""})
    args, _ = service.repo.create.call_args
    assert args[0]["license_expire_date"] is None


@pytest.mark.asyncio
async def test_update_employee_sets_license_idcard(service):
    e = make_mock_employee()
    service.repo.get_by_id.return_value = e

    async def update_side_effect(obj, data):
        for k, val in data.items():
            setattr(obj, k, val)
        return obj

    service.repo.update.side_effect = update_side_effect
    result = await service.update_employee(SAMPLE_EMPLOYEE_ID, {"license_no": "D333333333", "license_type": "D",
                                                                "license_expire_date": "2028-01-15T00:00:00",
                                                                "id_card_front_url": "/uploads/202607/c.png"})
    assert result["license_no"] == "D333333333"
    assert result["license_type"] == "D"
    assert result["license_expire_date"] == "2028-01-15T00:00:00"
    assert result["id_card_front_url"] == "/uploads/202607/c.png"


# ── 工号生成（EMP 分支回归） ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_employee_no_increments():
    from app.services.number_generator import generate_employee_no
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "007"
    db.execute = AsyncMock(return_value=result)
    no = await generate_employee_no(db)
    assert no == "008"


@pytest.mark.asyncio
async def test_generate_employee_no_empty_db():
    from app.services.number_generator import generate_employee_no
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    no = await generate_employee_no(db)
    assert no == "001"
