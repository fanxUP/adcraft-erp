"""Auditable reconciliation of historical finance facts; never a new payment source."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FinancePaymentDateReconciliation(Base, TimestampMixin):
    """Evidence-backed date allocation for an already-recorded paid amount."""

    __tablename__ = "finance_payment_date_reconciliations"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('expense', 'project_cost', 'outsource_task', 'outsource_payment')",
            name="ck_finance_payment_recon_source_type",
        ),
        CheckConstraint("amount > 0", name="ck_finance_payment_recon_amount_positive"),
        CheckConstraint(
            "evidence_type IN ('bank_statement', 'payment_voucher', 'other')",
            name="ck_finance_payment_recon_evidence_type",
        ),
        CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="ck_finance_payment_recon_evidence_reference",
        ),
        Index(
            "uq_finance_payment_recon_active_outsource_payment",
            "source_type",
            "source_id",
            unique=True,
            postgresql_where=text("source_type = 'outsource_payment' AND voided_at IS NULL"),
        ),
        Index(
            "ix_finance_payment_recon_source_active",
            "source_type",
            "source_id",
            "voided_at",
        ),
        Index("ix_finance_payment_recon_paid_at", "paid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    voided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinanceCostOverlapReview(Base, TimestampMixin):
    """Human conclusion for a suspected project-cost/outsource overlap."""

    __tablename__ = "finance_cost_overlap_reviews"
    __table_args__ = (
        UniqueConstraint(
            "project_cost_id",
            "outsource_task_id",
            name="uq_finance_cost_overlap_review_pair",
        ),
        CheckConstraint(
            "decision IN ('pending', 'confirmed_duplicate', 'confirmed_not_duplicate', 'needs_evidence')",
            name="ck_finance_cost_overlap_review_decision",
        ),
        CheckConstraint(
            "evidence_type IS NULL OR evidence_type IN ('bank_statement', 'payment_voucher', 'other')",
            name="ck_finance_cost_overlap_review_evidence_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_cost_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_costs.id", ondelete="RESTRICT"), nullable=False
    )
    outsource_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outsource_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    evidence_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
