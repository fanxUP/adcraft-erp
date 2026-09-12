import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid


class DesignTask(Base, TimestampMixin):
    __tablename__ = "design_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="design_task", lazy="selectin", cascade="all, delete-orphan",
        primaryjoin="and_(Attachment.related_type=='design_task', foreign(Attachment.related_id)==DesignTask.id)",
    )


class ProductionTask(Base, TimestampMixin):
    __tablename__ = "production_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    length: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    qc_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rework_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="production_task", lazy="selectin", cascade="all, delete-orphan", overlaps="attachments",
        primaryjoin="and_(Attachment.related_type=='production_task', foreign(Attachment.related_id)==ProductionTask.id)",
    )


class InstallationTask(Base, TimestampMixin):
    __tablename__ = "installation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    acceptance_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="installation_task", lazy="selectin", cascade="all, delete-orphan", overlaps="attachments",
        primaryjoin="and_(Attachment.related_type=='installation_task', foreign(Attachment.related_id)==InstallationTask.id)",
    )


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    __table_args__ = (
        Index(
            "ix_attachments_order_stage_created_at",
            "order_id",
            "stage",
            "created_at",
        ),
        CheckConstraint(
            "stage IS NULL OR stage IN ('design', 'production', 'installation')",
            name="ck_attachments_order_stage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    related_type: Mapped[str] = mapped_column(String(64), nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Order-stage attachments are owned by the order.  The polymorphic
    # related_type/related_id pair remains for old modules and provenance, but
    # it is no longer the authorization source for the three delivery stages.
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_documents.id"),
        nullable=True,
    )
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    design_task: Mapped["DesignTask | None"] = relationship(
        back_populates="attachments", foreign_keys=[related_id],
        primaryjoin="and_(Attachment.related_type=='design_task', foreign(Attachment.related_id)==DesignTask.id)",
        viewonly=True,
    )
    production_task: Mapped["ProductionTask | None"] = relationship(
        back_populates="attachments", foreign_keys=[related_id],
        primaryjoin="and_(Attachment.related_type=='production_task', foreign(Attachment.related_id)==ProductionTask.id)",
        viewonly=True,
    )
    installation_task: Mapped["InstallationTask | None"] = relationship(
        back_populates="attachments", foreign_keys=[related_id],
        primaryjoin="and_(Attachment.related_type=='installation_task', foreign(Attachment.related_id)==InstallationTask.id)",
        viewonly=True,
    )
    vehicle: Mapped["Vehicle | None"] = relationship(
        "Vehicle", foreign_keys=[related_id],
        primaryjoin="and_(Attachment.related_type=='vehicle', foreign(Attachment.related_id)==Vehicle.id)",
        viewonly=True,
    )
