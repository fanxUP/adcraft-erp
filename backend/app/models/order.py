import uuid

from sqlalchemy import DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.customer import Customer
from app.models.task import DesignTask, ProductionTask, InstallationTask


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sales_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="pending_confirm")
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    unpaid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    cost_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    delivery_deadline: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    installation_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship(lazy="selectin")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    status_logs: Mapped[list["OrderStatusLog"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    design_tasks: Mapped[list["DesignTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    production_tasks: Mapped[list["ProductionTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    installation_tasks: Mapped[list["InstallationTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    source_quote_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_items.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    length: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    width: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    height: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    subtotal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    operated_at: Mapped[str] = mapped_column(DateTime, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="status_logs")
