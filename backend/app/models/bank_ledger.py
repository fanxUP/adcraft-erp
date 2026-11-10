"""Opening balances and manually recorded cash movements for company accounts."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BankLedgerEntry(Base, TimestampMixin):
    __tablename__ = "bank_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('opening_balance', 'manual')",
            name="ck_bank_ledger_entry_type",
        ),
        CheckConstraint(
            "direction IN ('opening', 'income', 'expense')",
            name="ck_bank_ledger_direction",
        ),
        CheckConstraint(
            "(entry_type = 'opening_balance' AND direction = 'opening' AND amount >= 0) "
            "OR (entry_type = 'manual' AND direction IN ('income', 'expense') AND amount > 0)",
            name="ck_bank_ledger_amount_and_direction",
        ),
        Index("ix_bank_ledger_account_date", "account_id", "entry_date"),
        Index(
            "uq_bank_ledger_opening_per_account",
            "account_id",
            unique=True,
            postgresql_where=text("entry_type = 'opening_balance'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(String(200), nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
