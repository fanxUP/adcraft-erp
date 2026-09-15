import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskOrderItemLink(Base):
    """多态任务与订单明细的多值关联。"""

    __tablename__ = "task_order_item_links"
    __table_args__ = (
        UniqueConstraint(
            "task_type",
            "task_id",
            "order_item_id",
            name="uq_task_order_item_link",
        ),
        Index("ix_task_order_item_link_task", "task_type", "task_id"),
        Index("ix_task_order_item_link_item", "order_item_id"),
        Index("ix_task_order_item_link_task_status", "task_type", "task_id", "link_status"),
        Index("ix_task_order_item_link_item_status", "order_item_id", "link_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    item_progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 关联行本身有生命周期。删除订单明细时只移除当前关联，保留这行及其
    # 执行人/状态快照，供审计和回收站恢复使用。
    link_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    removed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    removed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
