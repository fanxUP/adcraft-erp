"""Canonical categories shared by manual ledger entries and project costs."""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FinanceCategory(Base, TimestampMixin):
    __tablename__ = "finance_categories"
    __table_args__ = (
        UniqueConstraint("name", name="uq_finance_categories_name"),
        UniqueConstraint("code", name="uq_finance_categories_code"),
        Index("ix_finance_categories_sort", "sort_order", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Stable identity for rules such as same-day fee ordering; renaming changes
    # only ``name`` and leaves this value intact.
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class FinanceCategoryAlias(Base, TimestampMixin):
    __tablename__ = "finance_category_aliases"
    __table_args__ = (
        UniqueConstraint("alias", name="uq_finance_category_aliases_alias"),
        Index("ix_finance_category_aliases_category", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alias: Mapped[str] = mapped_column(String(64), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("finance_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
