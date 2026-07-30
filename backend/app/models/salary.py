import uuid
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SalaryRecord(Base, TimestampMixin):
    __tablename__ = "salary_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    base_salary: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    overtime_pay: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    bonus: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    commission: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    subsidy: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    deduction: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    net_salary: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(16), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
