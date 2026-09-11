"""Add an independent executor to each task/order-item work unit."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "tio01_task_item_assignees"
down_revision: Union[str, None] = "tcd01_task_item_status_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is deliberately a nullable additive column.  Do not backfill it
    # from design_tasks/production_tasks/installation_tasks.assigned_to:
    # those legacy values represented a whole-task owner and cannot be safely
    # copied onto every order item in a mixed-progress task.
    op.add_column(
        "task_order_item_links",
        sa.Column(
            "assignee_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_task_order_item_links_assignee_user_id",
        "task_order_item_links",
        ["assignee_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_order_item_links_assignee_user_id",
        table_name="task_order_item_links",
    )
    op.drop_column("task_order_item_links", "assignee_user_id")
