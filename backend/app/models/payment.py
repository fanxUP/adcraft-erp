import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Legacy order link. New contract-scoped receipts may be split across
    # several orders or remain contract-level, so the allocation table is the
    # source of truth and this compatibility link is nullable.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_voided: Mapped[bool] = mapped_column(Boolean, default=False)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    document: Mapped["BusinessDocument"] = relationship(lazy="selectin")
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PaymentAllocation(Base, TimestampMixin):
    """Immutable business allocation of a receipt to a contract/order.

    The payment header records money received. This table records why the
    money reduces a contract receivable and, when possible, which order it
    belongs to. A contract-only allocation has a null document_id.
    """

    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint(
            "allocated_amount > 0",
            name="ck_payment_allocations_amount_positive",
        ),
        CheckConstraint(
            "allocation_type IN ('order', 'contract')",
            name="ck_payment_allocations_type",
        ),
        CheckConstraint(
            "(allocation_type = 'contract' AND document_id IS NULL) "
            "OR (allocation_type = 'order' AND document_id IS NOT NULL)",
            name="ck_payment_allocations_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    allocation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="order", comment="order | contract"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    payment: Mapped["Payment"] = relationship(back_populates="allocations")
    contract: Mapped["Contract"] = relationship(lazy="selectin")
    document: Mapped["BusinessDocument | None"] = relationship(lazy="selectin")


class CustomerStatement(Base, TimestampMixin):
    __tablename__ = "customer_statements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_order_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_unpaid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    customer: Mapped["Customer"] = relationship(lazy="selectin")


class Expense(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
