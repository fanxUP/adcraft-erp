import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import Date, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SalaryRule(Base, TimestampMixin):
    __tablename__ = "salary_rules"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_salary_rules_employee"),)  # 一人一条
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)  # 月工资标准
    social_insurance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)  # 社保金额
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
