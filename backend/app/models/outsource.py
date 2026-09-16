import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.business_document import BusinessDocumentItem


class OutsourceVendor(Base, TimestampMixin, SoftDeleteMixin):
    """统一供应商主数据。

    ``supplier_type=outsource`` 保持旧版外协任务和外协付款兼容；材料、
    设备及其他供应商共用同一主表，避免多套名称造成对账困难。
    """
    __tablename__ = "outsource_vendors"

    __table_args__ = (
        CheckConstraint(
            "tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100)",
            name="ck_outsource_vendors_tax_rate_range",
        ),
        CheckConstraint(
            "settlement_days IS NULL OR (settlement_days >= 0 AND settlement_days <= 3650)",
            name="ck_outsource_vendors_settlement_days_range",
        ),
        Index("ix_outsource_vendors_supplier_type", "supplier_type"),
        Index("ix_outsource_vendors_active_name", "is_active", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # production, installation, design, transport
    coop_rating: Mapped[str | None] = mapped_column(String(16), nullable=True)  # A, B, C
    supplier_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="outsource", server_default="outsource",
        comment="outsource/material/equipment/transport/service/other",
    )
    short_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    settlement_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    settlement_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    tasks: Mapped[list["OutsourceTask"]] = relationship(viewonly=True, lazy="selectin")


class OutsourceTask(Base, TimestampMixin, SoftDeleteMixin):
    """外协任务"""
    __tablename__ = "outsource_tasks"

    __table_args__ = (
        Index("ix_outsource_order_item", "order_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outsource_vendors.id"), nullable=False)
    related_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True
    )
    related_doc_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_task_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # design, production, installation 来源内部任务类型
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # 来源内部任务 id
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)  # production, installation, design, transport
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    unpaid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, in_progress, completed, settled
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    vendor: Mapped["OutsourceVendor"] = relationship(
        lazy="selectin",
        foreign_keys=[vendor_id],
    )

    order_item: Mapped["BusinessDocumentItem | None"] = relationship(
        BusinessDocumentItem,
        lazy="selectin",
        foreign_keys=[order_item_id],
    )


class OutsourcePayment(Base, TimestampMixin):
    """外协付款"""
    __tablename__ = "outsource_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outsource_vendors.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("outsource_tasks.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payee_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    vendor: Mapped["OutsourceVendor"] = relationship(
        lazy="selectin",
        foreign_keys=[vendor_id],
    )
