"""Tests for SalaryRecordService.generate_month (按工资规则自动生成工资表).

mock 模式：patch repo 类 + patch service 私有查询 helper，聚焦口径计算。
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.salary_grid import SalaryItem
from app.services.salary_service import SalaryRecordService

EMP1 = uuid4()
EMP2 = uuid4()


def make_rule(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", uuid4())
    r.employee_id = kwargs.get("employee_id", EMP1)
    r.effective_date = kwargs.get("effective_date", date(2026, 1, 1))
    r.base_salary = kwargs.get("base_salary", 5000.0)
    r.social_insurance = kwargs.get("social_insurance", None)
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
    rule = make_rule(base_salary=5000.0, social_insurance=500.0)
    await _patch_queries(service, rule=rule)
    result = await service.generate_month("2026-07")
    assert result["created"] == 1
    assert result["skipped_no_rule"] == 0
    data = service.repo.create.call_args[0][0]
    assert data["employee_id"] == EMP1
    assert data["month"] == "2026-07"
    assert data["base_salary"] == 5000.0
    assert data["subsidy"] == 0.0  # 补贴标准已从规则移除，恒 0
    assert data["deduction"] == 500.0  # 仅社保金额
    assert data["overtime_pay"] == 0.0
    assert data["bonus"] == 0.0
    assert data["commission"] == 0
    assert data["net_salary"] == 5000.0 - 500.0
    assert data["payment_status"] == "pending"


@pytest.mark.asyncio
async def test_generate_month_computes_overtime_and_bonus(service):
    rule = make_rule(base_salary=5000.0)
    await _patch_queries(service, rule=rule, overtime=10.0)
    result = await service.generate_month("2026-07")
    assert result["created"] == 1
    data = service.repo.create.call_args[0][0]
    hourly = 5000.0 / 21.75 / 8
    expected_overtime = round(10.0 * hourly * 1.5, 2)  # 加班费率已从规则移除，固定 1.5
    assert data["overtime_pay"] == expected_overtime
    assert data["bonus"] == 0.0  # 绩效标准已从规则移除，恒 0
    assert data["net_salary"] == round(5000.0 + expected_overtime, 2)


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
    rule = make_rule(social_insurance=500.0)
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
    assert row["attendance_bonus"] == 0.0  # 全勤标准已从规则移除，回退 0
    assert row["performance"] == 0.0  # 绩效标准已从规则移除，回退 0
    assert row["base_salary"] == 5000.0
    assert row["overtime_hours"] == 10.5
    assert row["overtime_pay"] == 100.0
    assert row["total_salary"] == 5100.0  # 5000+100
    assert row["performance_wage"] == 0.0  # 绩效标准已从规则移除
    assert row["meal_subsidy"] == 0.0  # 补贴标准已从规则移除，回退 0
    assert row["attendance_phone_subsidy"] == 0.0  # 全勤标准已从规则移除
    assert row["gross"] == 5100.0  # 5000+100+0+0
    assert row["social_deduction"] == 500.0  # 仅社保金额
    assert row["net_salary"] == 4600.0  # 5100-500
    assert row["social_insurance"] == 500.0
    assert row["actual_gross"] == 4600.0
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
    rule = make_rule(base_salary=5000.0)
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 20, "half": 0, "missed": 0, "absent": 0, "records": 20, "overtime": 10}})
    service._latest_rule = AsyncMock(return_value=rule)
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={})
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    service._upsert_record = AsyncMock()

    result = await service.compute_month("2026-07")
    assert result["computed"] == 1
    assert result["errors"] == []
    hourly = 5000 / 21.75 / 8
    assert seen["basic"] == 5000.0
    assert seen["overtime_pay"] == round(10 * hourly * 1.5, 2)  # ot_rate 已从规则移除恒 0 → (ot_rate or 1.5)=1.5
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
    service._latest_rule = AsyncMock(return_value=make_rule())
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    # 有旷工 → 不发全勤
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 20, "half": 0, "missed": 1, "absent": 0, "records": 21, "overtime": 0}})
    await service.compute_month("2026-07")
    assert seen["att_bonus"] == 0.0
    # 全勤 → 条件为真，但 att_bonus 已无规则来源恒 0
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 23, "half": 0, "missed": 0, "absent": 0, "records": 23, "overtime": 0}})
    await service.compute_month("2026-07")
    assert seen["att_bonus"] == 0.0


@pytest.mark.asyncio
async def test_compute_month_collects_eval_errors(service):
    # 公式合法但该员工触发除零 → 计入 errors，不中断
    items = [{"key": "x", "formula": "100 / (work_days - records)", "is_active": True}]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule())
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={})
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
    service._grid_values = AsyncMock(return_value={(str(EMP1), "hot"): (200.0, "manual")})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)
        seen["_manual"] = set(manual_keys)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["basic"] == 5000.0
    assert seen["hot"] == 200.0  # 手工值保留
    assert seen["_manual"] == {"hot"}


@pytest.mark.asyncio
async def test_compute_month_injects_month_params(service):
    # 公式引用自定义参数 hot_std（非内置变量），当月填 200 → bonus = 5000*0.2
    items = [{"key": "bonus", "formula": "base * hot_std", "is_active": True}]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(base_salary=5000.0))
    service._attendance_stats = AsyncMock(return_value={})
    service._param_values_for_month = AsyncMock(return_value={"hot_std": 0.2})
    service._grid_values = AsyncMock(return_value={})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["bonus"] == 1000.0  # 5000 * 0.2


@pytest.mark.asyncio
async def test_compute_month_preserves_manually_edited_cell(service):
    # 用户手动改过 basic=5600（source=manual）→ ⚡计算 不再覆盖它，且依赖列 gross 用钉住值重算
    items = [
        {"key": "basic", "formula": "base", "is_active": True},
        {"key": "gross", "formula": "basic", "is_active": True},
    ]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(base_salary=5000.0))
    service._attendance_stats = AsyncMock(return_value={})
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={
        (str(EMP1), "basic"): (5600.0, "manual"),
        (str(EMP1), "gross"): (5000.0, "computed"),
    })
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)
        seen["_manual"] = set(manual_keys)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["basic"] == 5600.0  # 手工钉住值保留
    assert seen["gross"] == 5600.0  # 依赖列用钉住值重新计算
    assert seen["_manual"] == {"basic"}  # 落库时保留 manual 标记，下次也不会被覆盖


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


# ── 三层分组表头：分组字段 + 新公式链 ───────────────────────────────────────

@pytest.mark.asyncio
async def test_create_item_accepts_groups(service):
    service._all_item_keys = AsyncMock(return_value=["basic"])
    service._all_param_keys = AsyncMock(return_value=[])
    service.db = _grid_session()
    item = await service.create_item({
        "key": "other_base", "label": "其他", "formula": "", "is_manual": True,
        "group1": "应发金额", "group2": "基本部分"})
    assert item["group1"] == "应发金额"
    assert item["group2"] == "基本部分"
    # 无分组 → None
    item2 = await service.create_item({"key": "last_net", "label": "上月实发工资",
                                       "formula": "", "is_manual": True})
    assert item2["group1"] is None
    assert item2["group2"] is None


@pytest.mark.asyncio
async def test_update_item_accepts_groups(service):
    item = MagicMock()
    item.id = uuid4()
    item.key = "custom"
    item.is_manual = False
    service._all_item_keys = AsyncMock(return_value=["custom"])
    service._all_param_keys = AsyncMock(return_value=[])
    service.db = _grid_session(item)
    updated = await service.update_item(item.id, {"group1": "应扣金额", "group2": ""})
    assert updated["group1"] == "应扣金额"
    assert item.group2 is None  # 空串清空


@pytest.mark.asyncio
async def test_compute_month_new_formula_chain(service):
    # 标准工资表口径：基本部分合计→应发合计→应扣合计→实发
    items = [
        {"key": "basic", "formula": "base", "is_active": True, "is_manual": False},
        {"key": "overtime_pay", "formula": "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)",
         "is_active": True, "is_manual": False},
        {"key": "att_bonus", "formula": "att_bonus if (missed_days == 0 and absent_days == 0) else 0",
         "is_active": True, "is_manual": False},
        {"key": "subsidy", "formula": "subsidy_std", "is_active": True, "is_manual": False},
        {"key": "other_base", "formula": "", "is_active": True, "is_manual": True},
        {"key": "base_total", "formula": "basic + overtime_pay + att_bonus + subsidy + other_base",
         "is_active": True, "is_manual": False},
        {"key": "bonus", "formula": "bonus_std", "is_active": True, "is_manual": False},
        {"key": "other_bonus", "formula": "", "is_active": True, "is_manual": True},
        {"key": "bonus_total", "formula": "bonus + other_bonus", "is_active": True, "is_manual": False},
        {"key": "absent_days", "formula": "absent_days", "is_active": True, "is_manual": False},
        {"key": "absent_deduction", "formula": "absent_days * (base / 21.75)",
         "is_active": True, "is_manual": False},
        {"key": "gross", "formula": "base_total + bonus_total - absent_deduction",
         "is_active": True, "is_manual": False},
        {"key": "social", "formula": "social", "is_active": True, "is_manual": False},
        {"key": "other_deduction", "formula": "", "is_active": True, "is_manual": True},
        {"key": "deduction", "formula": "social + other_deduction", "is_active": True, "is_manual": False},
        {"key": "net", "formula": "max(0, gross - deduction)", "is_active": True, "is_manual": False},
    ]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(
        base_salary=5000.0, social_insurance=200.0))
    service._attendance_stats = AsyncMock(return_value={
        str(EMP1): {"normal": 23, "half": 0, "missed": 0, "absent": 0, "records": 23, "overtime": 0}})
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={})
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["basic"] == 5000.0
    assert seen["subsidy"] == 0.0  # 补贴标准已从规则移除，恒 0
    assert seen["bonus"] == 0.0  # 绩效标准已从规则移除，恒 0
    assert seen["base_total"] == 5000.0  # 5000 + 0 + 0 + 0 + 0
    assert seen["bonus_total"] == 0.0  # 0 + 0
    assert seen["absent_days"] == 0.0
    assert seen["absent_deduction"] == 0.0
    assert seen["gross"] == 5000.0  # 5000 + 0 - 0
    assert seen["deduction"] == 200.0
    assert seen["net"] == 4800.0  # 5000 - 200


@pytest.mark.asyncio
async def test_compute_month_pins_manual_other_and_recomputes_total(service):
    # 手工填了其他(other_base)=100 → 钉住；合计(base_total) 用钉住值重算
    items = [
        {"key": "basic", "formula": "base", "is_active": True},
        {"key": "other_base", "formula": "", "is_active": True, "is_manual": True},
        {"key": "base_total", "formula": "basic + other_base", "is_active": True},
    ]
    service.list_items = AsyncMock(return_value=items)
    service._active_employees = AsyncMock(return_value=[MagicMock(id=EMP1)])
    service._latest_rule = AsyncMock(return_value=make_rule(base_salary=5000.0))
    service._attendance_stats = AsyncMock(return_value={})
    service._param_values_for_month = AsyncMock(return_value={})
    service._grid_values = AsyncMock(return_value={
        (str(EMP1), "other_base"): (100.0, "manual"),
    })
    service._upsert_record = AsyncMock()
    seen = {}

    async def fake_replace(month, eid, vals, manual_keys=()):
        seen.update(vals)
        seen["_manual"] = set(manual_keys)

    service._replace_grid_values = fake_replace
    await service.compute_month("2026-07")
    assert seen["other_base"] == 100.0  # 手工钉住值保留
    assert seen["base_total"] == 5100.0  # 5000 + 100
    assert seen["_manual"] == {"other_base"}


@pytest.mark.asyncio
async def test_save_cells_remark(service):
    service.list_items = AsyncMock(return_value=[])
    existing = make_record()
    service._existing_record = AsyncMock(return_value=existing)
    result = await service.save_cells("2026-07",
                                      remarks=[{"employee_id": str(EMP1), "remark": "旷工扣款"}])
    assert result["saved"] == 0
    data = service.repo.update.call_args[0][1]
    assert data["remark"] == "旷工扣款"


# ── 指标设置模板（命名保存 + 一键应用）─────────────────────────────────────

def _tpl(**kw):
    t = MagicMock()
    t.id = kw.get("id", uuid4())
    t.name = kw.get("name", "正式版")
    t.items = kw.get("items", [])
    return t


def _res(scalar=None, scalars=None):
    res = MagicMock()
    res.scalar_one_or_none.return_value = scalar
    res.scalars.return_value.all.return_value = scalars
    return res


def _item_mock(key, **kw):
    it = MagicMock()
    it.id = kw.get("id", uuid4())
    it.key = key
    it.is_builtin = kw.get("is_builtin", False)
    it.is_active = kw.get("is_active", True)
    return it


SNAP_FULL = [
    {"key": "basic", "label": "基本工资", "formula": "base", "sort_order": 1, "is_active": True, "is_manual": False, "group1": "应发金额", "group2": None},
    {"key": "net", "label": "实发工资", "formula": "max(0, basic - social)", "sort_order": 2, "is_active": True, "is_manual": False, "group1": None, "group2": None},
    {"key": "hot", "label": "高温补贴", "formula": "200", "sort_order": 3, "is_active": True, "is_manual": True, "group1": None, "group2": None},
]


@pytest.mark.asyncio
async def test_list_templates(service):
    service.db = MagicMock()
    service.db.execute = AsyncMock(return_value=_res(scalars=[_tpl(name="正式版", items=[{"key": "a"}, {"key": "b"}]),
                                                          _tpl(name="简化版", items=[{"key": "a"}])]))
    out = await service.list_templates()
    assert len(out) == 2
    assert out[0]["name"] == "正式版" and out[0]["item_count"] == 2
    assert out[1]["name"] == "简化版" and out[1]["item_count"] == 1


@pytest.mark.asyncio
async def test_create_template_validates(service):
    service._all_param_keys = AsyncMock(return_value=["commission_rate"])
    service.db = MagicMock()
    service.db.execute = AsyncMock(return_value=_res(scalar=None))  # 无同名
    service.db.add = MagicMock()
    service.db.flush = AsyncMock()
    tpl = await service.create_template("正式版", list(SNAP_FULL))
    assert tpl["name"] == "正式版"
    assert tpl["item_count"] == 3
    with pytest.raises(ValueError, match="只能包含"):
        await service.create_template("坏key", [{"key": "1bad", "label": "x", "formula": "1"}])
    with pytest.raises(ValueError, match="重复"):
        await service.create_template("重复key", [
            {"key": "a", "label": "x", "formula": "1"},
            {"key": "a", "label": "y", "formula": "1"},
        ])
    with pytest.raises(ValueError, match="未知变量"):
        await service.create_template("坏公式", [{"key": "bad", "label": "x", "formula": "nope + 1"}])


@pytest.mark.asyncio
async def test_create_template_duplicate_name(service):
    service.db = MagicMock()
    service.db.execute = AsyncMock(return_value=_res(scalar=_tpl(name="正式版")))
    with pytest.raises(ValueError, match="已存在"):
        await service.create_template("正式版", list(SNAP_FULL))


@pytest.mark.asyncio
async def test_update_and_delete_template(service):
    t = _tpl(name="旧名", items=[{"key": "basic", "label": "x", "formula": "1"}])
    s = MagicMock()
    s.execute = AsyncMock(side_effect=[_res(scalar=t), _res(scalar=None), _res(scalar=t)])  # 查重返回 None
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.delete = AsyncMock()
    service.db = s
    updated = await service.update_template(t.id, name="新名")
    assert t.name == "新名"
    assert updated["name"] == "新名"
    await service.delete_template(t.id)
    service.db.delete.assert_called_with(t)


@pytest.mark.asyncio
async def test_apply_template_reconciles(service):
    t = _tpl(name="正式版", items=list(SNAP_FULL))
    basic = _item_mock("basic", is_builtin=True, is_active=True)      # 命中模板 → 更新
    gone = _item_mock("old_extra", is_active=True)                    # 不在模板 → 停用
    gone_builtin = _item_mock("attend_days", is_builtin=True, is_active=True)  # 内置不在模板 → 停用
    s = MagicMock()
    s.execute = AsyncMock(return_value=_res(scalar=t, scalars=[basic, gone, gone_builtin]))
    s.add = MagicMock()
    s.flush = AsyncMock()
    service.db = s
    service._all_param_keys = AsyncMock(return_value=[])
    service.list_items = AsyncMock(return_value=[{"key": "basic"}])
    out = await service.apply_template(t.id)
    # 命中模板的现有指标被更新（is_builtin 保持）
    assert basic.label == "基本工资"
    assert basic.formula == "base"
    assert basic.sort_order == 1
    assert basic.is_active is True
    assert basic.is_builtin is True
    # 不在模板的指标停用（保留数据）
    assert gone.is_active is False
    assert gone_builtin.is_active is False
    # 模板新增的指标被创建（非内置；手工列公式清空）
    added = {c.args[0].key: c.args[0] for c in s.add.call_args_list if isinstance(c.args[0], SalaryItem)}
    assert set(added) == {"net", "hot"}
    assert added["net"].is_builtin is False and added["net"].formula == "max(0, basic - social)"
    assert added["hot"].is_manual is True and added["hot"].formula == ""
    # 返回应用后的指标列表
    assert out == [{"key": "basic"}]


@pytest.mark.asyncio
async def test_apply_template_invalid_formula_blocks(service):
    t = _tpl(name="坏模板", items=[{"key": "bad", "label": "x", "formula": "nope + 1", "sort_order": 1, "is_active": True, "is_manual": False, "group1": None, "group2": None}])
    s = MagicMock()
    s.execute = AsyncMock(return_value=_res(scalar=t, scalars=[]))
    s.add = MagicMock()
    s.flush = AsyncMock()
    service.db = s
    service._all_param_keys = AsyncMock(return_value=[])
    with pytest.raises(ValueError, match="未知变量"):
        await service.apply_template(t.id)
    s.add.assert_not_called()


@pytest.mark.asyncio
async def test_apply_template_keeps_existing_reserved_key_item(service):
    # 现有指标 key 与系统变量同名（历史内置列，如 missed_days/absent_days/social）→ 应用应正常更新
    t = _tpl(name="正式版", items=[
        {"key": "missed_days", "label": "旷工", "formula": "missed_days", "sort_order": 1, "is_active": True, "is_manual": False, "group1": None, "group2": None},
    ])
    missed = _item_mock("missed_days", is_builtin=True, is_active=True)
    s = MagicMock()
    s.execute = AsyncMock(return_value=_res(scalar=t, scalars=[missed]))
    s.add = MagicMock()
    s.flush = AsyncMock()
    service.db = s
    service._all_param_keys = AsyncMock(return_value=[])
    service.list_items = AsyncMock(return_value=[{"key": "missed_days"}])
    out = await service.apply_template(t.id)
    assert missed.label == "旷工"
    assert missed.is_active is True
    assert out == [{"key": "missed_days"}]
    s.add.assert_not_called()


@pytest.mark.asyncio
async def test_apply_template_refuses_new_reserved_key(service):
    # 模板里"新建"一个与系统变量同名的 key（库里不存在）→ 拒绝
    t = _tpl(name="坏模板", items=[
        {"key": "base", "label": "新列", "formula": "1", "sort_order": 1, "is_active": True, "is_manual": False, "group1": None, "group2": None},
    ])
    s = MagicMock()
    s.execute = AsyncMock(return_value=_res(scalar=t, scalars=[]))
    s.add = MagicMock()
    s.flush = AsyncMock()
    service.db = s
    service._all_param_keys = AsyncMock(return_value=[])
    with pytest.raises(ValueError, match="无法新建"):
        await service.apply_template(t.id)
    s.add.assert_not_called()
