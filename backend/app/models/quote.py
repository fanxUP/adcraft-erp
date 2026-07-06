import uuid

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Quote(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sales_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    subtotal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    valid_until: Mapped[str | None] = mapped_column(Date, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="部门/科室")

    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote", lazy="selectin", cascade="all, delete-orphan")


class QuoteItem(Base, TimestampMixin):
    __tablename__ = "quote_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    length: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    length_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    width: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    width_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    height: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    height_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    use_area: Mapped[bool] = mapped_column(default=False)
    quantity_mode: Mapped[str] = mapped_column(String(16), default="piece")
    area: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    process_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    installation_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    design_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    transport_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    other_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    subtotal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    material_process: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)

    quote: Mapped["Quote"] = relationship(back_populates="items")


class QuoteVersion(Base, TimestampMixin):
    __tablename__ = "quote_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
