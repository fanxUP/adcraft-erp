import uuid

from sqlalchemy import DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DesignTask(Base, TimestampMixin):
    __tablename__ = "design_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
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
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    length: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    width: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    height: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1)
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
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    related_type: Mapped[str] = mapped_column(String(64), nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
