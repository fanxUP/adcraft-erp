import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class ProjectCost(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "project_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True
    )
    document_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_document_items.id", ondelete="SET NULL"), nullable=True
    )
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="分项名（1级分组）")
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True, comment="数量")
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="规格尺寸")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True, comment="单价")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="付款方式：现金支付/微信支付/转账支付/对公支付/其它支付")
    payee_company_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="对方收款公司名称")
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outsource_vendors.id", ondelete="SET NULL"), nullable=True,
        comment="统一供应商主数据ID",
    )
    debt_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True, default=0, comment="欠款金额")
    is_debt: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为欠款")
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, comment="欠款是否已结清")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="欠款结清时间")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="成本摘要")
    cost_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    document: Mapped["BusinessDocument | None"] = relationship(foreign_keys=[document_id], lazy="selectin")
    document_item: Mapped["BusinessDocumentItem | None"] = relationship(foreign_keys=[document_item_id], lazy="selectin")
    item_links: Mapped[list["ProjectCostItemLink"]] = relationship(
        back_populates="project_cost",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    customer: Mapped["Customer"] = relationship(lazy="selectin")
    supplier: Mapped["OutsourceVendor | None"] = relationship(
        "OutsourceVendor", foreign_keys=[supplier_id], lazy="selectin"
    )


class ProjectCostItemLink(Base, TimestampMixin):
    """订单成本与订单明细的多值归属关系，不承载金额分摊。"""

    __tablename__ = "project_cost_item_links"
    __table_args__ = (
        UniqueConstraint(
            "project_cost_id",
            "document_item_id",
            name="uq_project_cost_item_link",
        ),
        Index("ix_project_cost_item_links_cost", "project_cost_id"),
        Index("ix_project_cost_item_links_item", "document_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_cost_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_costs.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="RESTRICT"),
        nullable=False,
    )

    project_cost: Mapped["ProjectCost"] = relationship(back_populates="item_links")
    document_item: Mapped["BusinessDocumentItem"] = relationship(lazy="selectin")
