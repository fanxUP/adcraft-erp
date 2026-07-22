import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class AcceptanceForm(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "acceptance_forms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acceptance_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    our_acceptor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    advance_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    order: Mapped["Order"] = relationship(lazy="selectin")
    our_acceptor: Mapped["User"] = relationship(foreign_keys=[our_acceptor_id], lazy="selectin")
    items: Mapped[list["AcceptanceItem"]] = relationship(back_populates="acceptance", cascade="all, delete-orphan", lazy="selectin")
    attachments: Mapped[list["AcceptanceAttachment"]] = relationship(back_populates="acceptance", cascade="all, delete-orphan", lazy="selectin")


class AcceptanceItem(Base, TimestampMixin):
    __tablename__ = "acceptance_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acceptance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("acceptance_forms.id"), nullable=False)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_process: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specification: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    area: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    item_status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    acceptance: Mapped["AcceptanceForm"] = relationship(back_populates="items")


class AcceptanceAttachment(Base, TimestampMixin):
    __tablename__ = "acceptance_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acceptance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("acceptance_forms.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    filesize: Mapped[int | None] = mapped_column(nullable=True)
    upload_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    acceptance: Mapped["AcceptanceForm"] = relationship(back_populates="attachments")
