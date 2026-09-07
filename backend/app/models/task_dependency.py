import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


TASK_TYPE_CHECK = "predecessor_task_type IN ('design', 'production', 'installation') AND successor_task_type IN ('design', 'production', 'installation')"


class TaskDependency(Base, TimestampMixin):
    """A finish-to-start edge between two tasks in the same order.

    The three task tables use different models, so the references are
    intentionally polymorphic.  The service layer validates that both IDs
    exist and belong to the same order before an edge is inserted.
    """

    __tablename__ = "task_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    predecessor_task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    predecessor_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    successor_task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    successor_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dependency_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="finish_to_start", server_default="finish_to_start"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(TASK_TYPE_CHECK, name="ck_task_dependencies_task_types"),
        CheckConstraint(
            "dependency_type = 'finish_to_start'",
            name="ck_task_dependencies_type",
        ),
        CheckConstraint(
            "predecessor_task_type <> successor_task_type OR predecessor_task_id <> successor_task_id",
            name="ck_task_dependencies_not_self",
        ),
        UniqueConstraint(
            "predecessor_task_type",
            "predecessor_task_id",
            "successor_task_type",
            "successor_task_id",
            name="uq_task_dependencies_edge",
        ),
        Index(
            "ix_task_dependencies_successor",
            "successor_task_type",
            "successor_task_id",
        ),
        Index(
            "ix_task_dependencies_predecessor",
            "predecessor_task_type",
            "predecessor_task_id",
        ),
    )
