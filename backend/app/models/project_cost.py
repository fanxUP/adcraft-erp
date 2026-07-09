import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class ProjectCost(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "project_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), default="order", comment="来源类型：order/quote")
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True)
    quote_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_items.id"), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, comment="数量")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, comment="单价")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="付款方式：现金支付/微信支付/转账支付/对公支付/其它支付")
    payee_company_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="对方收款公司名称")
    debt_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, default=0, comment="欠款金额")
    is_debt: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为欠款")
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, comment="欠款是否已结清")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="欠款结清时间")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="成本摘要")
    cost_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    order: Mapped["Order"] = relationship(lazy="selectin")
    quote: Mapped["Quote"] = relationship(lazy="selectin")
    order_item: Mapped["OrderItem | None"] = relationship(lazy="selectin")
    quote_item: Mapped["QuoteItem | None"] = relationship(lazy="selectin")
    customer: Mapped["Customer"] = relationship(lazy="selectin")
