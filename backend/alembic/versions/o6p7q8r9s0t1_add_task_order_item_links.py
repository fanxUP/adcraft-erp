"""Link delivery tasks to order items without rewriting historical tasks."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "o6p7q8r9s0t1"
down_revision = "n5o6p7q8r9s0"
branch_labels = None
depends_on = None


_TASK_TABLES = ("design_tasks", "production_tasks", "installation_tasks")


def upgrade() -> None:
    for table in _TASK_TABLES:
        op.add_column(
            table,
            sa.Column(
                "order_item_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            f"fk_{table}_order_item_id",
            table,
            "business_document_items",
            ["order_item_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_{table}_order_item_id",
            table,
            ["order_item_id"],
        )


def downgrade() -> None:
    for table in reversed(_TASK_TABLES):
        op.drop_index(f"ix_{table}_order_item_id", table_name=table)
        op.drop_constraint(
            f"fk_{table}_order_item_id",
            table,
            type_="foreignkey",
        )
        op.drop_column(table, "order_item_id")
