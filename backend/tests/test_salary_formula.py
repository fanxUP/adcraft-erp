"""Tests for salary_formula: 受限 AST 公式求值器。"""

import pytest

from app.services.salary_formula import (
    FormulaError,
    build_dependency_order,
    evaluate_formula,
    validate_formula,
)


def test_arithmetic():
    assert evaluate_formula("base + ot_hours * 2", {"base": 5000, "ot_hours": 10}) == 5020.0
    assert evaluate_formula("(base - 1000) / 2", {"base": 5000}) == 2000.0


def test_overtime_pay_formula():
    f = "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)"
    assert evaluate_formula(f, {"ot_hours": 10, "base": 5000, "ot_rate": 2.0}) == pytest.approx(10 * 5000 / 174 * 2)
    # ot_rate 为 0 → or 兜底 1.5
    assert evaluate_formula(f, {"ot_hours": 10, "base": 5000, "ot_rate": 0}) == pytest.approx(10 * 5000 / 174 * 1.5)


def test_conditional():
    f = "att_bonus if (missed_days == 0 and absent_days == 0) else 0"
    assert evaluate_formula(f, {"att_bonus": 300, "missed_days": 0, "absent_days": 0}) == 300.0
    assert evaluate_formula(f, {"att_bonus": 300, "missed_days": 1, "absent_days": 0}) == 0.0
    assert evaluate_formula(f, {"att_bonus": 300, "missed_days": 0, "absent_days": 3}) == 0.0


def test_functions():
    assert evaluate_formula("max(0, gross - deduction)", {"gross": 5000, "deduction": 6000}) == 0.0
    assert evaluate_formula("round(100.567, 2)", {}) == 100.57
    assert evaluate_formula("abs(-5)", {}) == 5.0
    assert evaluate_formula("min(3, 5)", {}) == 3.0


def test_comparison_and_not():
    assert evaluate_formula("not (a > 10)", {"a": 5}) == 1.0
    assert evaluate_formula("1 if a >= 5 else 0", {"a": 5}) == 1.0
    assert evaluate_formula("1 if a != 3 else 0", {"a": 5}) == 1.0


@pytest.mark.parametrize("bad", [
    "nope + 1",
    '"abc"',
    "base.__class__",
    "x[0]",
    "print(1)",
    "base.upper()",
    "[1, 2, 3]",
    "lambda x: x",
])
def test_invalid_formula_raises(bad):
    with pytest.raises(FormulaError):
        validate_formula(bad, {"base"})


def test_division_by_zero():
    with pytest.raises(FormulaError):
        evaluate_formula("base / 0", {"base": 1})


def test_cycle_detection():
    with pytest.raises(FormulaError, match="循环引用"):
        build_dependency_order({"a": "b + 1", "b": "a + 1"})


def test_dependency_order():
    order = build_dependency_order({
        "net": "max(0, gross - deduction)",
        "gross": "basic + bonus",
        "basic": "base",
        "bonus": "bonus_std",
        "deduction": "social + housing",
    })
    assert order.index("basic") < order.index("gross") < order.index("net")
    assert order.index("deduction") < order.index("net")


def test_validate_returns_referenced_keys():
    refs = validate_formula("gross + social", {"basic", "gross"})
    assert refs == {"gross"}  # social 是原始变量，不算指标依赖


def test_validate_function_name_not_unknown_var():
    # max/min/round/abs 是函数名，不算未知变量
    validate_formula("max(0, base - 100)", {"base"})


def test_validate_accepts_param_and_manual_keys():
    # 参数 key / 手工填写指标 key 通过 extra_keys 允许引用
    refs = validate_formula("base * hot_std + hot_subsidy",
                            {"base"}, {"hot_std", "hot_subsidy"})
    assert refs == {"base"}  # 只有指标 key 进入依赖图；参数/手工列是叶子
    with pytest.raises(FormulaError, match="未知变量"):
        validate_formula("base * hot_std", {"base"})


def test_build_dependency_order_with_extra_keys():
    # 公式引用参数/手工列 key 不影响拓扑排序（它们不参与依赖图）
    order = build_dependency_order(
        {"gross": "basic + hot_subsidy", "basic": "base"},
        {"hot_subsidy", "commission_rate"},
    )
    assert order.index("basic") < order.index("gross")
