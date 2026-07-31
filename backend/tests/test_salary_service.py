"""Tests for SalaryRecordService.generate_month (按工资规则自动生成工资表).

mock 模式：patch repo 类 + patch service 私有查询 helper，聚焦口径计算。
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.salary_service import SalaryRecordService

EMP1 = uuid4()
EMP2 = uuid4()


def make_rule(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", uuid4())
    r.employee_id = kwargs.get("employee_id", EMP1)
    r.effective_date = kwargs.get("effective_date", date(2026, 1, 1))
    r.base_salary = kwargs.get("base_salary", 5000.0)
    r.overtime_rate = kwargs.get("overtime_rate", 1.5)
    r.bonus_standard = kwargs.get("bonus_standard", None)
    r.commission_rate = kwargs.get("commission_rate", None)
    r.subsidy_standard = kwargs.get("subsidy_standard", None)
    r.attendance_bonus = kwargs.get("attendance_bonus", None)
    r.social_insurance = kwargs.get("social_insurance", None)
    r.housing_fund = kwargs.get("housing_fund", None)
    r.deduction_standard = kwargs.get("deduction_standard", None)
    return r


@pytest.fixture
def service():
    repo = MagicMock()
    repo.create = AsyncMock()
    with patch("app.services.salary_service.SalaryRecordRepository") as MockRepo:
        MockRepo.return_value = repo
        svc = SalaryRecordService(MagicMock())
        svc.repo = repo
        yield svc


async def _patch_queries(svc, **overrides):
    svc._active_employees = AsyncMock(return_value=overrides.get("active", [MagicMock(id=EMP1)]))
    svc._latest_rule = AsyncMock(return_value=overrides.get("rule", make_rule()))
    svc._existing_record = AsyncMock(return_value=overrides.get("existing", None))
    svc._monthly_overtime_hours = AsyncMock(return_value=overrides.get("overtime", 0.0))


# ── 生成主流程 ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_month_skips_employee_without_rule(service):
    await _patch_queries(service, rule=None)
    result = await service.generate_month("2026-07")
    assert result["created"] == 0
    assert result["skipped_no_rule"] == 1
    service.repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_month_creates_record_with_rule_components(service):
    rule = make_rule(base_salary=5000.0, subsidy_standard=300.0, social_insurance=500.0,
                     housing_fund=300.0, deduction_standard=100.0)
    await _patch_queries(service, rule=rule)
    result = await service.generate_month("2026-07")
    assert result["created"] == 1
    assert result["skipped_no_rule"] == 0
    data = service.repo.create.call_args[0][0]
    assert data["employee_id"] == EMP1
    assert data["month"] == "2026-07"
    assert data["base_salary"] == 5000.0
    assert data["subsidy"] == 300.0
    assert data["deduction"] == 900.0
    assert data["overtime_pay"] == 0.0
    assert data["bonus"] == 0.0
    assert data["commission"] == 0
    assert data["net_salary"] == 5000.0 + 300.0 - 900.0
    assert data["payment_status"] == "pending"


@pytest.mark.asyncio
async def test_generate_month_computes_overtime_and_bonus(service):
    rule = make_rule(base_salary=5000.0, overtime_rate=2.0, bonus_standard=200.0)
    await _patch_queries(service, rule=rule, overtime=10.0)
    result = await service.generate_month("2026-07")
    assert result["created"] == 1
    data = service.repo.create.call_args[0][0]
    hourly = 5000.0 / 21.75 / 8
    expected_overtime = round(10.0 * hourly * 2.0, 2)
    assert data["overtime_pay"] == expected_overtime
    assert data["bonus"] == 200.0
    assert data["net_salary"] == round(5000.0 + expected_overtime + 200.0, 2)


@pytest.mark.asyncio
async def test_generate_month_skips_existing_record(service):
    await _patch_queries(service, existing=MagicMock())
    result = await service.generate_month("2026-07")
    assert result["skipped_exists"] == 1
    assert result["created"] == 0
    service.repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_month_uses_given_employee_ids(service):
    rule = make_rule(employee_id=EMP2)
    await _patch_queries(service, rule=rule)
    result = await service.generate_month("2026-07", [EMP2])
    service._active_employees.assert_not_called()
    assert result["created"] == 1
    assert service.repo.create.call_args[0][0]["employee_id"] == EMP2


@pytest.mark.asyncio
async def test_generate_month_net_clamped_at_zero(service):
    rule = make_rule(base_salary=1000.0, social_insurance=2000.0)
    await _patch_queries(service, rule=rule)
    result = await service.generate_month("2026-07")
    assert result["created"] == 1
    data = service.repo.create.call_args[0][0]
    assert data["net_salary"] == 0.0


@pytest.mark.asyncio
async def test_generate_month_invalid_month_raises(service):
    await _patch_queries(service)
    with pytest.raises(ValueError, match="YYYY-MM"):
        await service.generate_month("2026/07")
    service.repo.create.assert_not_called()
