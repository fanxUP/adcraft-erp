import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, SoftDeleteMixin

class Employee(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resignation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(16), default="active")
    id_card: Mapped[str | None] = mapped_column(String(32), nullable=True)
    license_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="驾驶证号")
    license_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="驾驶证类型")
    license_expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="驾驶证到期日")
    id_card_front_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="身份证正面照片")
    id_card_back_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="身份证反面照片")
    education: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)