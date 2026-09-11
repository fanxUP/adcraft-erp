import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskItemStatusLog(Base):
    """Append-only history for one task stage and one order item.

    ``task_id`` is intentionally polymorphic because the three delivery task
    tables share the same item-processing contract but are not backed by one
    joined task table.  The stage discriminator keeps the history explicit.
    """

    __tablename__ = "task_item_status_logs"
    __table_args__ = (
        Index(
            "ix_tcd_status_document_item",
            "document_id",
            "task_type",
            "order_item_id",
            "operated_at",
        ),
        Index(
            "ix_tcd_status_assignee_time",
            "assignee_user_id",
            "operated_at",
        ),
        Index(
            "ix_tcd_status_stage_time",
            "task_type",
            "to_status",
            "operated_at",
        ),
        Index(
            "ix_tcd_status_item_stage_time",
            "order_item_id",
            "task_type",
            "operated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    operated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Live events always have a timestamp.  Historical backfill can be
    # timestamp-less when the old snapshot did not retain a reliable time;
    # such rows are eligible for "全部" but never for "当月".
    operated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="live",
        server_default="live",
    )
