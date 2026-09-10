"""Add order-level employee visibility assignments for delivery tasks."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "tavp01_order_task_assignees"
down_revision: Union[str, None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_task_assignees",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["business_documents.id"],
            name="fk_order_task_assignees_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_order_task_assignees_employee",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name="fk_order_task_assignees_assigned_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "document_id",
            "employee_id",
            name="uq_order_task_assignee_document_employee",
        ),
    )
    op.create_index(
        "ix_order_task_assignees_document",
        "order_task_assignees",
        ["document_id"],
    )
    op.create_index(
        "ix_order_task_assignees_employee",
        "order_task_assignees",
        ["employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_task_assignees_employee", table_name="order_task_assignees")
    op.drop_index("ix_order_task_assignees_document", table_name="order_task_assignees")
    op.drop_table("order_task_assignees")
