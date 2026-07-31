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
    repo.update = AsyncMock()
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


# ── 工资报表 report_month ────────────────────────────────────────────────────

def make_record(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", uuid4())
    r.employee_id = kwargs.get("employee_id", EMP1)
    r.month = kwargs.get("month", "2026-07")
    r.base_salary = kwargs.get("base_salary", 5000.0)
    r.overtime_pay = kwargs.get("overtime_pay", 0.0)
    r.bonus = kwargs.get("bonus", None)
    r.commission = kwargs.get("commission", None)
    r.subsidy = kwargs.get("subsidy", None)
    r.deduction = kwargs.get("deduction", None)
    r.net_salary = kwargs.get("net_salary", 0.0)
    r.payment_status = kwargs.get("payment_status", "pending")
    r.remark = kwargs.get("remark", None)
    return r


def make_employee(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", EMP1)
    e.employee_no = kwargs.get("employee_no", "E001")
    e.name = kwargs.get("name", "张三")
    e.department = kwargs.get("department", "design")
    return e


def _setup_report(service, records, prev_records=None, employees=None, rule=None, att=None, att_grid=None):
    """mock 报表依赖：repo.list(当月, 上月) + 员工/规则/考勤查询。"""
    prev_records = prev_records if prev_records is not None else []
    employees = employees if employees is not None else [make_employee() for _ in records]
    service.repo.list = AsyncMock(side_effect=[(records, len(records)), (prev_records, len(prev_records))])
    service._load_employee = AsyncMock(side_effect=employees)
    service._latest_rule = AsyncMock(return_value=rule if rule is not None else make_rule())
    service._attendance_stats = AsyncMock(return_value=att or {})
    service._grid_values = AsyncMock(return_value=att_grid or {})
    return service


@pytest.mark.asyncio
async def test_report_month_returns_row_fields(service):
    record = make_record(base_salary=5000.0, overtime_pay=100.0, remark="备注")
    rule = make_rule(attendance_bonus=300.0, bonus_standard=200.0, subsidy_standard=50.0,
                     social_insurance=500.0, housing_fund=300.0, deduction_standard=100.0)
    att = {str(EMP1): {"normal": 20, "half": 2, "missed": 0, "absent": 1,
                       "records": 23, "overtime": 10.5}}
    _setup_report(service, [record], rule=rule, att=att)

    result = await service.report_month("2026-07")
    assert result["month"] == "2026-07"
    assert result["title"] == "2026年7月份工资计算明细表"
    row = result["rows"][0]
    assert row["employee_no"] == "E001"
    assert row["department"] == "design"
    assert row["employee_name"] == "张三"
    assert row["attend_days"] == 21.0  # 20 + 0.5*2
    assert row["missed_days"] == 0
    non_weekend = sum(1 for d in range(1, 32) if date(2026, 7, d).weekday() < 5)
    assert row["absent_days"] == max(0, non_weekend - 23) + 1
    assert row["attendance_bonus"] == 300.0
    assert row["performance"] == 200.0
    assert row["base_salary"] == 5000.0
    assert row["overtime_hours"] == 10.5
    assert row["overtime_pay"] == 100.0
    assert row["total_salary"] == 5100.0  # 5000+100
    assert row["performance_wage"] == 200.0
    assert row["meal_subsidy"] == 50.0
    assert row["attendance_phone_subsidy"] == 300.0
    assert row["gross"] == 5650.0  # 5100+200+50+300
    assert row["social_deduction"] == 900.0  # 500+300+100
    assert row["net_salary"] == 4750.0  # 5650-900
    assert row["social_insurance"] == 500.0
    assert row["actual_gross"] == 4750.0
    assert row["remark"] == "备注"
    assert row["prev_month_net"] is None


@pytest.mark.asyncio
async def test_report_month_uses_prev_month_net(service):
    record = make_record(base_salary=5000.0)
    prev_record = make_record(employee_id=EMP1, month="2026-06", net_salary=4800.0)
    _setup_report(service, [record], prev_records=[prev_record],
                  att={str(EMP1): {"normal": 20, "half": 0, "missed": 0, "absent": 0,
                                   "records": 20, "overtime": 0}})
    result = await service.report_month("2026-07")
    assert result["rows"][0]["prev_month_net"] == 4800.0


@pytest.mark.asyncio
async def test_report_month_no_rule_and_no_attendance_zero(service):
    record = make_record(base_salary=5000.0)
    _setup_report(service, [record], rule=None, att={})
    result = await service.report_month("2026-07")
    row = result["rows"][0]
    assert row["attendance_bonus"] == 0.0
    assert row["performance"] == 0.0
    assert row["meal_subsidy"] == 0.0
    assert row["social_deduction"] == 0.0
    assert row["attend_days"] == 0
    assert row["gross"] == 5000.0
    assert row["net_salary"] == 5000.0


@pytest.mark.asyncio
async def test_report_month_sorts_rows_by_department(service):
    r1 = make_record(employee_id=EMP1, base_salary=5000.0)
    r2 = make_record(employee_id=EMP2, base_salary=6000.0)
    emp1 = make_employee(id=EMP1, name="张三", department="design")
    emp2 = make_employee(id=EMP2, name="李四", department="admin")
    _setup_report(service, [r1, r2], employees=[emp1, emp2], att={})
    result = await service.report_month("2026-07")
    assert [r["department"] for r in result["rows"]] == ["admin", "design"]
    assert [r["employee_name"] for r in result["rows"]] == ["李四", "张三"]


@pytest.mark.asyncio
async def test_report_month_empty_returns_no_rows(service):
    _setup_report(service, [])
    result = await service.report_month("2026-07")
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_report_month_invalid_month_raises(service):
    _setup_report(service, [])
    with pytest.raises(ValueError, match="YYYY-MM"):
        await service.report_month("2026/07")


# ── 工资网格 compute/get_grid/save_cells / 指标 CRUD ────────────────────────

def _grid_session(item=None):
    """mock AsyncSession：execute 返回 item，支持 add/flush/delete。"""
    s = MagicMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = item
    s.execute = AsyncMock(return_value=res)
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.delete = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_compute_month_evaluates_formulas(service):
    items = [
        {"key": "basic", "formula": "base", "is_active": True},
        {"key": "overtime_pay", "formula": "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)", "is_active": True},
        {"key": "deduction", "formula": "social + housing", "is_active": True},
        {"key": "gross", "formula": "basic + overtime_pay", "is_active": True},
        {"key": "net", "formula": "max(0, gross - deduction)", "is_active": True},
    ]
    rule = make_rule(base_salary=5000.0, overtime_rate=2.0)
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 20, "half": 0, "missed": 0, "absent": 0, "records": 20, "overtime": 10}})
    service._latest_rule = AsyncMock(return_value=rule)
    service._param_values_for_month = AsyncMock(return_value={})
    seen = {}

    async def fake_replace(month, eid, vals):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    service._upsert_record = AsyncMock()

    result = await service.compute_month("2026-07")
    assert result["computed"] == 1
    assert result["errors"] == []
    hourly = 5000 / 21.75 / 8
    assert seen["basic"] == 5000.0
    assert seen["overtime_pay"] == round(10 * hourly * 2, 2)
    assert seen["deduction"] == 0.0
    assert seen["gross"] == round(5000 + seen["overtime_pay"], 2)
    assert seen["net"] == seen["gross"]
    service._upsert_record.assert_awaited_once()


@pytest.mark.asyncio
async def test_compute_month_attendance_conditional(service):
    items = [{"key": "att_bonus", "formula": "att_bonus if (missed_days == 0 and absent_days == 0) else 0",
              "is_active": True}]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(attendance_bonus=300.0))
    service._param_values_for_month = AsyncMock(return_value={})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    # 有旷工 → 不发全勤
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 20, "half": 0, "missed": 1, "absent": 0, "records": 21, "overtime": 0}})
    await service.compute_month("2026-07")
    assert seen["att_bonus"] == 0.0
    # 全勤 → 发全勤
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 23, "half": 0, "missed": 0, "absent": 0, "records": 23, "overtime": 0}})
    await service.compute_month("2026-07")
    assert seen["att_bonus"] == 300.0


@pytest.mark.asyncio
async def test_compute_month_collects_eval_errors(service):
    # 公式合法但该员工触发除零 → 计入 errors，不中断
    items = [{"key": "x", "formula": "100 / (work_days - records)", "is_active": True}]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule())
    service._param_values_for_month = AsyncMock(return_value={})
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 23, "half": 0, "missed": 0, "absent": 0, "records": 23, "overtime": 0}})
    service._load_employee = AsyncMock(return_value=make_employee())
    service._replace_grid_values = AsyncMock()
    service._upsert_record = AsyncMock()
    result = await service.compute_month("2026-07")
    assert result["computed"] == 0
    assert len(result["errors"]) == 1
    assert "除数为 0" in result["errors"][0]


@pytest.mark.asyncio
async def test_upsert_record_creates_when_missing(service):
    service._existing_record = AsyncMock(return_value=None)
    await service._upsert_record("2026-07", EMP1,
                                 {"basic": 5000, "overtime_pay": 100, "bonus": 200,
                                  "subsidy": 50, "deduction": 900, "net": 4450})
    data = service.repo.create.call_args[0][0]
    assert data["employee_id"] == EMP1
    assert data["month"] == "2026-07"
    assert data["base_salary"] == 5000.0
    assert data["net_salary"] == 4450.0
    assert data["payment_status"] == "pending"
    service.repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_record_updates_existing(service):
    service._existing_record = AsyncMock(return_value=make_record(net_salary=1000))
    await service._upsert_record("2026-07", EMP1,
                                 {"basic": 6000, "overtime_pay": 0, "bonus": 0,
                                  "subsidy": 0, "deduction": 0, "net": 6000})
    data = service.repo.update.call_args[0][1]
    assert data["base_salary"] == 6000.0
    assert data["net_salary"] == 6000.0
    service.repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_grid_returns_items_and_rows(service):
    service.list_items = AsyncMock(return_value=[
        {"key": "basic", "label": "基本工资", "formula": "base", "sort_order": 1,
         "is_active": True, "is_builtin": True, "id": "1"},
        {"key": "net", "label": "实发工资", "formula": "max(0, gross - deduction)", "sort_order": 2,
         "is_active": True, "is_builtin": True, "id": "2"},
    ])
    service._active_employees = AsyncMock(return_value=[make_employee()])
    service._grid_values = AsyncMock(return_value={(str(EMP1), "basic"): 5000.0})
    service.repo.list = AsyncMock(return_value=([make_record(net_salary=4400.0, payment_status="paid")], 1))

    result = await service.get_grid("2026-07")
    assert result["month"] == "2026-07"
    assert len(result["items"]) == 2
    row = result["rows"][0]
    assert row["employee_no"] == "E001"
    assert row["values"]["basic"] == 5000.0
    assert row["values"]["net"] is None
    assert row["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_save_cells_persists_manual_and_syncs_record(service):
    service.list_items = AsyncMock(return_value=[
        {"key": "basic", "is_active": True}, {"key": "net", "is_active": True},
        {"key": "custom", "is_active": True}])
    upserted = {}

    async def fake_upsert(month, eid, key, value, source):
        upserted[key] = (value, source)

    service._upsert_grid_value = fake_upsert
    service._grid_values = AsyncMock(return_value={(str(EMP1), "basic"): 5500.0})
    service._existing_record = AsyncMock(return_value=make_record())

    result = await service.save_cells("2026-07",
                                      cells=[{"employee_id": str(EMP1), "item_key": "basic", "value": 5500}])
    assert result["saved"] == 1
    assert upserted["basic"] == (5500.0, "manual")
    service.repo.update.assert_called_once()
    assert service.repo.update.call_args[0][1]["base_salary"] == 5500.0


@pytest.mark.asyncio
async def test_save_cells_payment_status(service):
    service.list_items = AsyncMock(return_value=[])
    existing = make_record(payment_status="pending")
    service._existing_record = AsyncMock(return_value=existing)
    result = await service.save_cells("2026-07",
                                      payments=[{"employee_id": str(EMP1), "payment_status": "paid"}])
    assert result["saved"] == 0
    data = service.repo.update.call_args[0][1]
    assert data["payment_status"] == "paid"
    assert data["paid_at"] is not None


@pytest.mark.asyncio
async def test_create_item_validates_formula(service):
    service._all_item_keys = AsyncMock(return_value=["basic"])
    service._all_param_keys = AsyncMock(return_value=["commission_rate"])
    service.db = _grid_session()
    item = await service.create_item({"key": "hot", "label": "高温补贴", "formula": "base * 0.1"})
    assert item["key"] == "hot"
    assert item["is_builtin"] is False
    assert item["is_manual"] is False
    with pytest.raises(ValueError, match="未知变量"):
        await service.create_item({"key": "bad", "label": "错误", "formula": "nope + 1"})
    with pytest.raises(ValueError, match="同名"):
        await service.create_item({"key": "base", "label": "冲突", "formula": "1"})
    # 公式可引用参数 key
    await service.create_item({"key": "ok", "label": "正常", "formula": "base * commission_rate"})


@pytest.mark.asyncio
async def test_update_item_and_delete_builtin(service):
    item = MagicMock()
    item.id = uuid4()
    item.key = "basic"
    item.is_builtin = True
    item.is_manual = False
    service._all_item_keys = AsyncMock(return_value=["basic", "net"])
    service._all_param_keys = AsyncMock(return_value=[])
    service.db = _grid_session(item)
    updated = await service.update_item(item.id, {"formula": "base * 2"})
    assert item.formula == "base * 2"
    with pytest.raises(ValueError, match="内置指标"):
        await service.delete_item(item.id)


# ── 手工填写指标 + 每月参数 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_manual_item_skips_formula_validation(service):
    service._all_item_keys = AsyncMock(return_value=["basic"])
    service._all_param_keys = AsyncMock(return_value=[])
    service.db = _grid_session()
    item = await service.create_item({"key": "hot", "label": "高温补贴", "formula": "", "is_manual": True})
    assert item["is_manual"] is True
    assert item["formula"] == ""


@pytest.mark.asyncio
async def test_update_item_switch_to_manual_clears_formula(service):
    item = MagicMock()
    item.id = uuid4()
    item.key = "hot"
    item.is_manual = False
    item.formula = "base * 0.1"
    service.db = _grid_session(item)
    updated = await service.update_item(item.id, {"is_manual": True})
    assert updated["is_manual"] is True
    assert item.formula == ""


@pytest.mark.asyncio
async def test_compute_month_skips_manual_items_and_preserves_cells(service):
    # 手工填写列不参与公式计算，原有值在 ⚡计算 后保留
    items = [
        {"key": "basic", "formula": "base", "is_active": True, "is_manual": False},
        {"key": "hot", "formula": "", "is_active": True, "is_manual": True},
    ]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(base_salary=5000.0))
    service._attendance_stats = AsyncMock(return_value={})
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={(str(EMP1), "hot"): 200.0})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["basic"] == 5000.0
    assert seen["hot"] == 200.0  # 手工值保留


@pytest.mark.asyncio
async def test_compute_month_injects_month_params(service):
    # 公式引用自定义参数 hot_std（非内置变量），当月填 200 → bonus = 5000*0.2
    items = [{"key": "bonus", "formula": "base * hot_std", "is_active": True}]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(base_salary=5000.0))
    service._attendance_stats = AsyncMock(return_value={})
    service._param_values_for_month = AsyncMock(return_value={"hot_std": 0.2})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["bonus"] == 1000.0  # 5000 * 0.2


@pytest.mark.asyncio
async def test_compute_month_all_manual_raises(service):
    items = [{"key": "hot", "formula": "", "is_active": True, "is_manual": True}]
    service.list_items = AsyncMock(return_value=items)
    with pytest.raises(ValueError, match="公式指标"):
        await service.compute_month("2026-07")


@pytest.mark.asyncio
async def test_create_param_validate_key(service):
    service._all_item_keys = AsyncMock(return_value=["basic"])
    service._all_param_keys = AsyncMock(return_value=["commission_rate"])
    service.db = _grid_session()
    p = await service.create_param({"key": "hot_std", "label": "高温补贴标准"})
    assert p["key"] == "hot_std"
    with pytest.raises(ValueError, match="同名"):
        await service.create_param({"key": "commission_rate", "label": "重复"})
    with pytest.raises(ValueError, match="同名"):
        await service.create_param({"key": "basic", "label": "冲突"})


@pytest.mark.asyncio
async def test_list_params_with_month_value(service):
    param = MagicMock()
    param.id = uuid4()
    param.key = "commission_rate"
    param.label = "提成系数"
    param.sort_order = 1
    val = MagicMock()
    val.param_id = param.id
    val.value = 0.05
    res_params = MagicMock()
    res_params.scalars.return_value.all.return_value = [param]
    res_vals = MagicMock()
    res_vals.scalars.return_value.all.return_value = [val]
    service.db = MagicMock()
    service.db.execute = AsyncMock(side_effect=[res_params, res_vals])
    result = await service.list_params("2026-07")
    assert result["month"] == "2026-07"
    assert result["params"][0]["key"] == "commission_rate"
    assert result["params"][0]["value"] == 0.05


@pytest.mark.asyncio
async def test_save_param_values_upserts_and_clears(service):
    param = MagicMock()
    param.id = uuid4()
    param.key = "commission_rate"
    existing = MagicMock()
    existing.value = 0.1
    res_params = MagicMock()
    res_params.scalars.return_value.all.return_value = [param]
    res_row = MagicMock()
    res_row.scalar_one_or_none.return_value = existing
    service.db = MagicMock()
    # 第一次查询参数列表 → 第二次查该参数当月值（upsert）→ 第三次查该参数当月值（清空）
    service.db.execute = AsyncMock(side_effect=[res_params, res_row, res_row])
    service.db.flush = AsyncMock()
    service.db.add = MagicMock()
    service.db.delete = AsyncMock()

    r = await service.save_param_values("2026-07", [
        {"key": "commission_rate", "value": 0.05},
        {"key": "commission_rate", "value": None},
    ])
    assert r["saved"] == 1
    assert existing.value == 0.05
    service.db.delete.assert_called_once()
