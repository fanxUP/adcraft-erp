import uuid
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SalaryRecord(Base, TimestampMixin):
    __tablename__ = "salary_records"
    __table_args__ = (UniqueConstraint("employee_id", "month", name="uq_salary_employee_month"),)
    snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expense_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("expenses.id", ondelete="RESTRICT"), nullable=True, unique=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    overtime_pay: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    bonus: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    commission: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    subsidy: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    deduction: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(16), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
