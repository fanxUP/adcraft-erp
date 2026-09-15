"""Keep order-item deletion history while removing current task scope."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "oid01_item_delete_consistency"
down_revision: Union[str, None] = "branding01_system_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TASK_TABLES = ("design_tasks", "production_tasks", "installation_tasks")


def upgrade() -> None:
    op.add_column(
        "task_order_item_links",
        sa.Column("link_status", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.add_column("task_order_item_links", sa.Column("removed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "task_order_item_links",
        sa.Column("removed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("task_order_item_links", sa.Column("removed_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_task_order_item_links_removed_by",
        "task_order_item_links",
        "users",
        ["removed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_task_order_item_link_task_status",
        "task_order_item_links",
        ["task_type", "task_id", "link_status"],
    )
    op.create_index(
        "ix_task_order_item_link_item_status",
        "task_order_item_links",
        ["order_item_id", "link_status"],
    )
    op.create_check_constraint(
        "ck_task_order_item_links_link_status",
        "task_order_item_links",
        "link_status IN ('active', 'removed')",
    )

    for table_name in _TASK_TABLES:
        op.add_column(
            table_name,
            sa.Column("scope_status", sa.String(length=32), nullable=False, server_default="active"),
        )
        op.add_column(table_name, sa.Column("scope_closed_at", sa.DateTime(), nullable=True))
        op.add_column(table_name, sa.Column("scope_closed_reason", sa.Text(), nullable=True))
        op.create_check_constraint(
            f"ck_{table_name}_scope_status",
            table_name,
            "scope_status IN ('active', 'empty_after_item_delete')",
        )


def downgrade() -> None:
    for table_name in reversed(_TASK_TABLES):
        op.drop_constraint(f"ck_{table_name}_scope_status", table_name, type_="check")
        op.drop_column(table_name, "scope_closed_reason")
        op.drop_column(table_name, "scope_closed_at")
        op.drop_column(table_name, "scope_status")

    op.drop_constraint(
        "ck_task_order_item_links_link_status",
        "task_order_item_links",
        type_="check",
    )
    op.drop_index(
        "ix_task_order_item_link_item_status",
        table_name="task_order_item_links",
    )
    op.drop_index(
        "ix_task_order_item_link_task_status",
        table_name="task_order_item_links",
    )
    op.drop_constraint(
        "fk_task_order_item_links_removed_by",
        "task_order_item_links",
        type_="foreignkey",
    )
    op.drop_column("task_order_item_links", "removed_reason")
    op.drop_column("task_order_item_links", "removed_by")
    op.drop_column("task_order_item_links", "removed_at")
    op.drop_column("task_order_item_links", "link_status")
