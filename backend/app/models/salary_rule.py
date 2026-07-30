import uuid
from datetime import date
from sqlalchemy import Date, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SalaryRule(Base, TimestampMixin):
    __tablename__ = "salary_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    overtime_rate: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)  # 加班费率
    bonus_standard: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 奖金标准
    commission_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 提成比例(%)
    subsidy_standard: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 补贴标准/月
    attendance_bonus: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 全勤奖
    social_insurance: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 社保扣款
    housing_fund: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 公积金扣款
    deduction_standard: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 其他扣款标准
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
