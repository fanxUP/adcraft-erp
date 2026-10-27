"""Company-owned payment accounts, independent from supplier bank details."""
import uuid

from sqlalchemy import Boolean, CheckConstraint, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CompanyAccount(Base, TimestampMixin):
    __tablename__ = "company_accounts"
    __table_args__ = (
        CheckConstraint("account_type IN ('bank', 'wechat', 'alipay', 'cash', 'other')", name="ck_company_account_type"),
        CheckConstraint("NOT is_default OR is_active", name="ck_company_account_default_active"),
        Index("uq_company_account_default", "is_default", unique=True, postgresql_where=text("is_default = true")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    holder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
