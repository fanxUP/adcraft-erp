import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalaryItem(Base, TimestampMixin):
    """工资指标定义（网格的一列）：key + 标签 + 可编辑公式。

    预置 11 个内置指标（is_builtin=true），允许新增自定义指标列。
    公式为 Python 风格表达式（见 app/services/salary_formula.py）。
    """
    __tablename__ = "salary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False, default="0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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
