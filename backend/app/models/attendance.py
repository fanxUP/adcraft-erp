import uuid
from datetime import date, datetime, time
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class AttendanceRule(Base, TimestampMixin):
    __tablename__ = "attendance_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    check_in_time: Mapped[time] = mapped_column(Time, nullable=False)
    check_out_time: Mapped[time] = mapped_column(Time, nullable=False)
    work_days: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    late_threshold: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_threshold: Mapped[int] = mapped_column(Integer, default=0)
    overtime_rate: Mapped[float | None] = mapped_column(Numeric(3, 1), default=1.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_status: Mapped[str] = mapped_column(String(16), default="normal")
    check_out_status: Mapped[str] = mapped_column(String(16), default="normal")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    overtime_hours: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True, default=0)
