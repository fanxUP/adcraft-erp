import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalaryItem(Base, TimestampMixin):
    """工资指标定义（网格的一列）：key + 标签 + 可编辑公式。

    预置内置指标（is_builtin=true），允许新增自定义指标列。
    公式为 Python 风格表达式（见 app/services/salary_formula.py）。
    group1/group2 用于三层分组表头（应发金额→基本部分/绩效部分/未出勤…），
    为空表示独立列（占满三层高度）。
    """
    __tablename__ = "salary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False, default="0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 手工填写列：无公式，⚡计算不覆盖，值由用户逐格填写
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 三层分组表头：group1=一级组（应发金额/应扣金额/代缴部分），group2=二级组（基本部分/绩效部分/未出勤）
    group1: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group2: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SalaryItemTemplate(Base, TimestampMixin):
    """工资指标设置模板：命名保存的指标配置快照，可一键应用覆盖当前指标。

    items 为 JSON 数组，每个元素形如 _item_d 但去掉 id/is_builtin：
    {key, label, formula, sort_order, is_active, is_manual, group1, group2}。
    """
    __tablename__ = "salary_item_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class SalaryGridValue(Base, TimestampMixin):
    """工资网格单元格值：某月某员工某指标的值。

    source: computed(公式算出) | manual(手工修改)。生成会覆盖 computed，
    手工修改的单元格保留 manual 标记。
    """
    __tablename__ = "salary_grid_values"
    __table_args__ = (
        UniqueConstraint("month", "employee_id", "item_key", name="uq_salary_grid_month_emp_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="computed")


class SalaryParam(Base, TimestampMixin):
    """工资参数定义：每月手工填一个值，公式里可直接引用其 key。

    例如参数 key=commission_rate、label=提成系数，某月填 0.05，
    则该月所有员工的公式里 commission_rate 都等于 0.05。
    """
    __tablename__ = "salary_params"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SalaryParamValue(Base, TimestampMixin):
    """某月某参数的取值；未填的参数在公式中按 0 处理。"""
    __tablename__ = "salary_param_values"
    __table_args__ = (
        UniqueConstraint("month", "param_id", name="uq_salary_param_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    param_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("salary_params.id"), nullable=False
    )
    value: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
