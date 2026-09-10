"""Order-level visibility assignments for delivery tasks."""

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OrderTaskAssignee(Base, TimestampMixin):
    """An employee allowed to see tasks belonging to one order.

    An empty set of rows means that the order is intentionally unassigned and
    remains visible to every employee who has the relevant task permission.
    Employees are soft-deleted/deactivated rather than removed, so the
    visibility query also checks the employee's current active binding.
    """

    __tablename__ = "order_task_assignees"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "employee_id",
            name="uq_order_task_assignee_document_employee",
        ),
        Index("ix_order_task_assignees_document", "document_id"),
        Index("ix_order_task_assignees_employee", "employee_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
