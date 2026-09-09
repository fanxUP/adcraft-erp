"""Track per-order-item task state and remove unused manual dependencies."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "q8r9s0t1u2v3"
down_revision: Union[str, None] = "p7q8r9s0t1u2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task_order_item_links",
        sa.Column("item_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "task_order_item_links",
        sa.Column("item_progress_pct", sa.Integer(), nullable=True),
    )
    op.add_column(
        "task_order_item_links",
        sa.Column("item_completed_at", sa.DateTime(), nullable=True),
    )

    # Preserve the current aggregate state for any already-linked task. The
    # columns remain nullable so legacy rows can still be interpreted by the
    # service layer when a task was created before this migration.
    for task_type, table_name in (
        ("design", "design_tasks"),
        ("production", "production_tasks"),
        ("installation", "installation_tasks"),
    ):
        op.execute(
            sa.text(
                f"""
                UPDATE task_order_item_links AS link
                SET item_status = task.status,
                    item_progress_pct = task.progress_pct,
                    item_completed_at = task.completed_at
                FROM {table_name} AS task
                WHERE link.task_type = '{task_type}'
                  AND link.task_id = task.id
                  AND link.item_status IS NULL
                """
            )
        )

    # The production database was checked before this migration and contains
    # no manual dependency rows. Drop the unused graph after taking the
    # required backup; the old migration file remains in history for replay.
    op.execute(sa.text("DROP TABLE IF EXISTS task_dependencies"))


def downgrade() -> None:
    op.create_table(
        "task_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predecessor_task_type", sa.String(length=32), nullable=False),
        sa.Column("predecessor_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("successor_task_type", sa.String(length=32), nullable=False),
        sa.Column("successor_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "dependency_type",
            sa.String(length=32),
            nullable=False,
            server_default="finish_to_start",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_task_dependencies_created_by", ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "predecessor_task_type IN ('design', 'production', 'installation') "
            "AND successor_task_type IN ('design', 'production', 'installation')",
            name="ck_task_dependencies_task_types",
        ),
        sa.CheckConstraint(
            "dependency_type = 'finish_to_start'",
            name="ck_task_dependencies_type",
        ),
        sa.CheckConstraint(
            "predecessor_task_type <> successor_task_type OR predecessor_task_id <> successor_task_id",
            name="ck_task_dependencies_not_self",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "predecessor_task_type",
            "predecessor_task_id",
            "successor_task_type",
            "successor_task_id",
            name="uq_task_dependencies_edge",
        ),
    )
    op.create_index(
        "ix_task_dependencies_successor",
        "task_dependencies",
        ["successor_task_type", "successor_task_id"],
    )
    op.create_index(
        "ix_task_dependencies_predecessor",
        "task_dependencies",
        ["predecessor_task_type", "predecessor_task_id"],
    )
    op.drop_column("task_order_item_links", "item_completed_at")
    op.drop_column("task_order_item_links", "item_progress_pct")
    op.drop_column("task_order_item_links", "item_status")
