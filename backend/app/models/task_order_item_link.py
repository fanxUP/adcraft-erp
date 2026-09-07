import uuid

from sqlalchemy import Index, Integer, String, UniqueConstraint, ForeignKey
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
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
