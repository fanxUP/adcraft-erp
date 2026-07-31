"""工资指标公式引擎（受限 AST 求值器，stdlib 实现，无第三方依赖）。

公式为 Python 风格表达式，支持：
- 四则运算 + - * / % 与括号、一元负号
- 比较 == != < <= > >= ，逻辑 and/or/not
- 条件式 `A if 条件 else B`
- 函数 max / min / round / abs
- 引用原始变量（规则值/考勤统计）或其他指标列的 key

安全性：白名单节点类型求值，禁止属性访问、下标、调用任意函数、字符串/字节
字面量、推导式等，杜绝任意代码执行。
"""

import ast
from typing import Iterable

# 每个员工每月可用的原始变量（由调用方填值，缺省 0）
RAW_VARS: set[str] = {
    # 工资规则
    "base", "ot_rate", "bonus_std", "commission_rate", "subsidy_std",
    "att_bonus", "social", "housing", "ded_std",
    # 考勤统计
    "ot_hours", "attend_days", "half_days", "missed_days", "absent_days",
    "records", "work_days",
}

FUNCTIONS: set[str] = {"max", "min", "round", "abs"}

# 允许的二元运算符
_BINOPS = {
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
}
_UNARYOPS = {ast.UAdd, ast.USub, ast.Not}
_CMPOPS = {
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
}

# 便于前端帮助面板展示的变量说明
VARIABLE_HINTS: list[dict] = [
    {"name": "base", "label": "基本工资标准(规则)"},
    {"name": "ot_rate", "label": "加班费率(规则)"},
    {"name": "bonus_std", "label": "绩效标准(规则)"},
    {"name": "subsidy_std", "label": "伙食补助标准(规则)"},
    {"name": "att_bonus", "label": "全勤奖标准(规则)"},
    {"name": "social", "label": "社保(规则)"},
    {"name": "housing", "label": "公积金(规则)"},
    {"name": "ded_std", "label": "其他扣款(规则)"},
    {"name": "ot_hours", "label": "当月加班工时"},
    {"name": "attend_days", "label": "出勤天数"},
    {"name": "half_days", "label": "半天数"},
    {"name": "missed_days", "label": "旷工天数"},
    {"name": "absent_days", "label": "未出勤天数"},
    {"name": "records", "label": "有考勤记录天数"},
    {"name": "work_days", "label": "月内非周末天数"},
]

FORMULA_EXAMPLES: list[str] = [
    "加班费：ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)",
    "全勤奖：att_bonus if (missed_days == 0 and absent_days == 0) else 0",
    "实发工资：max(0, gross - deduction)",
    "出勤满勤才发全勤：200 if attend_days >= work_days else 100",
]


class FormulaError(ValueError):
    """公式不合法或求值失败，message 为中文提示。"""


def _to_number(v):
    """把变量值转成数字；None/空串按 0 处理，字符串/其他类型报错。"""
    if v is None or v == "":
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        raise FormulaError(f"公式引用的变量值不是数字：{v!r}")


class _Evaluator(ast.NodeVisitor):
    """受限 AST 求值器。变量不存在或节点非法时抛 FormulaError。"""

    def __init__(self, variables: dict, item_keys: set[str]):
        self.vars = {k: _to_number(v) for k, v in variables.items()}
        self.item_keys = item_keys

    def evaluate(self, node: ast.AST):
        return self.visit(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            return 1.0 if node.value else 0.0
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError(f"公式包含不允许的字面量：{node.value!r}")

    def visit_Name(self, node):
        v = self.vars.get(node.id)
        if v is None and node.id not in self.vars:
            raise FormulaError(f"公式引用了未知变量：{node.id}")
        return v

    def visit_BinOp(self, node):
        if type(node.op) not in _BINOPS:
            raise FormulaError("公式包含不允许的运算符")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
        except ZeroDivisionError:
            raise FormulaError("公式除数为 0")
        raise FormulaError("不支持的运算符")

    def visit_UnaryOp(self, node):
        if type(node.op) not in _UNARYOPS:
            raise FormulaError("公式包含不允许的一元运算符")
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        return 1.0 if not operand else 0.0  # not

    def visit_BoolOp(self, node):
        # 短路求值，保持 Python 语义（and/or 返回操作数本身）
        if isinstance(node.op, ast.And):
            result = self.visit(node.values[0])
            for v in node.values[1:]:
                if not result:
                    return result
                result = self.visit(v)
            return result
        if isinstance(node.op, ast.Or):
            result = self.visit(node.values[0])
            for v in node.values[1:]:
                if result:
                    return result
                result = self.visit(v)
            return result
        raise FormulaError("公式包含不允许的逻辑运算符")

    def visit_Compare(self, node):
        if any(type(op) not in _CMPOPS for op in node.ops):
            raise FormulaError("公式包含不允许的比较运算符")
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if type(op) is ast.Eq and not (left == right):
                return 0.0
            if type(op) is ast.NotEq and not (left != right):
                return 0.0
            if type(op) is ast.Lt and not (left < right):
                return 0.0
            if type(op) is ast.LtE and not (left <= right):
                return 0.0
            if type(op) is ast.Gt and not (left > right):
                return 0.0
            if type(op) is ast.GtE and not (left >= right):
                return 0.0
            left = right
        return 1.0

    def visit_IfExp(self, node):
        cond = self.visit(node.test)
        return self.visit(node.body if cond else node.orelse)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            raise FormulaError("公式只能调用 max / min / round / abs 函数")
        if node.keywords:
            raise FormulaError("公式函数调用不支持关键字参数")
        name = node.func.id
        args = [self.visit(a) for a in node.args]
        if name == "abs" and len(args) == 1:
            return abs(args[0])
        if name == "max" and len(args) >= 1:
            return max(args)
        if name == "min" and len(args) >= 1:
            return min(args)
        if name == "round" and len(args) in (1, 2):
            return round(args[0], int(args[1]) if len(args) == 2 else 0)
        raise FormulaError(f"函数 {name} 参数个数不正确")

    def generic_visit(self, node):
        raise FormulaError(f"公式包含不允许的语法：{type(node).__name__}")


def validate_formula(formula: str, item_keys: Iterable[str] = ()) -> set[str]:
    """校验公式语法与变量名，返回公式引用的指标列 key 集合。

    - 语法非法 / 含不允许的节点 → FormulaError
    - 引用未知变量（非 RAW_VARS 且非指标 key）→ FormulaError
    """
    if not formula or not formula.strip():
        raise FormulaError("公式不能为空")
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"公式语法错误：{e.msg}")
    keys = set(item_keys)
    # 先做节点类型合法性检查 + 收集 Name
    names: list[str] = []

    class _Check(ast.NodeVisitor):
        def visit_Name(self, node):
            names.append(node.id)

        def visit_Constant(self, node):
            if isinstance(node.value, bool):
                return
            if not isinstance(node.value, (int, float)):
                raise FormulaError(f"公式包含不允许的字面量：{node.value!r}")

        def generic_visit(self, node):
            # 复用求值器的白名单：这里做类型检查
            if type(node) not in _ALLOWED_NODES:
                raise FormulaError(f"公式包含不允许的语法：{type(node).__name__}")
            super().generic_visit(node)

    checker = _Check()
    try:
        checker.visit(tree)
    except FormulaError:
        raise
    except Exception as e:  # pragma: no cover - 防御
        raise FormulaError(f"公式校验失败：{e}")

    for n in names:
        if n in FUNCTIONS:
            continue  # max/min/round/abs 是函数名，不是变量
        if n not in RAW_VARS and n not in keys:
            raise FormulaError(f"公式引用了未知变量：{n}")
    return {n for n in names if n not in FUNCTIONS and n in keys}


_ALLOWED_NODES = {
    ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
    ast.BoolOp, ast.Compare, ast.IfExp, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
}


def build_dependency_order(item_formulas: dict) -> list:
    """按公式间依赖对指标 key 做拓扑排序（被依赖的先算）。

    item_formulas: {key: formula}。公式引用其他指标 key 形成依赖边。
    存在循环引用 → FormulaError。
    """
    keys = set(item_formulas)
    deps: dict = {k: set() for k in keys}
    for k, f in item_formulas.items():
        for ref in validate_formula(f, keys - {k}):
            if ref in keys and ref != k:
                deps[k].add(ref)

    ordered: list = []
    visited: dict = {}
    temp: set = set()

    def visit(k: str):
        state = visited.get(k)
        if state == "done":
            return
        if state == "doing":
            raise FormulaError(f"指标公式存在循环引用：{k}")
        visited[k] = "doing"
        for d in sorted(deps[k]):
            visit(d)
        visited[k] = "done"
        ordered.append(k)

    for k in keys:
        visit(k)
    return ordered


def evaluate_formula(formula: str, variables: dict, item_keys: Iterable[str] = ()) -> float:
    """求值单条公式。variables 为原始变量值 dict（缺省 0）。

    返回 float；语法/变量/求值错误均抛 FormulaError。
    """
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"公式语法错误：{e.msg}")
    return _Evaluator(variables, set(item_keys)).evaluate(tree)
