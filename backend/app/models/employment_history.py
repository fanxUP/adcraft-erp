import uuid
from datetime import date
from sqlalchemy import Date, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class EmploymentHistory(Base, TimestampMixin):
    __tablename__ = "employment_histories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    change_date: Mapped[date] = mapped_column(Date, nullable=False)
    change_type: Mapped[str] = mapped_column(String(16), nullable=False)  # hire/promotion/transfer/resignation
    previous_department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    previous_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
