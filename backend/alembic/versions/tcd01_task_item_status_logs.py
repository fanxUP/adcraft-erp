"""Track item-level task status events for completion metrics.

Revision ID: tcd01_task_item_status_logs
Revises: b1c2d3e4f5a6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "tcd01_task_item_status_logs"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _backfill_for_task(table_name: str, task_type: str, completed_statuses: tuple[str, ...]) -> None:
    statuses = ", ".join(f"'{status}'" for status in completed_statuses)
    op.execute(
        sa.text(
            f"""
            INSERT INTO task_item_status_logs
                (id, task_type, task_id, document_id, order_item_id,
                 from_status, to_status, assignee_user_id, operated_by,
                 operated_at, source)
            SELECT
                gen_random_uuid(),
                :task_type,
                l.task_id,
                t.document_id,
                l.order_item_id,
                NULL,
                l.item_status,
                NULL,
                NULL,
                l.item_completed_at,
                'backfill'
            FROM task_order_item_links l
            JOIN {table_name} t ON t.id = l.task_id
            JOIN business_documents d ON d.id = t.document_id
            JOIN business_document_items i ON i.id = l.order_item_id
            WHERE l.task_type = :task_type
              AND l.item_status IN ({statuses})
              AND d.doc_type = 'order'
              AND i.lifecycle_status = 'active'
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_item_status_logs existing
                  WHERE existing.task_type = l.task_type
                    AND existing.task_id = l.task_id
                    AND existing.order_item_id = l.order_item_id
              )
            """
        ).bindparams(task_type=task_type)
    )


def _backfill_legacy_task_column(table_name: str, task_type: str, completed_statuses: tuple[str, ...]) -> None:
    statuses = ", ".join(f"'{status}'" for status in completed_statuses)
    op.execute(
        sa.text(
            f"""
            INSERT INTO task_item_status_logs
                (id, task_type, task_id, document_id, order_item_id,
                 from_status, to_status, assignee_user_id, operated_by,
                 operated_at, source)
            SELECT
                gen_random_uuid(),
                :task_type,
                t.id,
                t.document_id,
                t.order_item_id,
                NULL,
                t.status,
                NULL,
                NULL,
                t.completed_at,
                'backfill'
            FROM {table_name} t
            JOIN business_documents d ON d.id = t.document_id
            JOIN business_document_items i ON i.id = t.order_item_id
            WHERE t.order_item_id IS NOT NULL
              AND t.status IN ({statuses})
              AND d.doc_type = 'order'
              AND i.lifecycle_status = 'active'
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_item_status_logs existing
                  WHERE existing.task_type = :task_type
                    AND existing.task_id = t.id
                    AND existing.order_item_id = t.order_item_id
              )
            """
        ).bindparams(task_type=task_type)
    )


def upgrade() -> None:
    op.create_table(
        "task_item_status_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("business_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("business_document_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column(
            "assignee_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "operated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("operated_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="live"),
    )
    op.create_index(
        "ix_tcd_status_document_item",
        "task_item_status_logs",
        ["document_id", "task_type", "order_item_id", "operated_at"],
    )
    op.create_index(
        "ix_tcd_status_assignee_time",
        "task_item_status_logs",
        ["assignee_user_id", "operated_at"],
    )
    op.create_index(
        "ix_tcd_status_stage_time",
        "task_item_status_logs",
        ["task_type", "to_status", "operated_at"],
    )
    op.create_index(
        "ix_tcd_status_item_stage_time",
        "task_item_status_logs",
        ["order_item_id", "task_type", "operated_at"],
    )

    # Backfill only the facts that existed in the old item snapshot.  A NULL
    # timestamp is intentional: it supports all-time reconciliation but is
    # excluded by month filtering because its completion time is unknown.
    _backfill_for_task("design_tasks", "design", ("confirmed", "completed"))
    _backfill_for_task("production_tasks", "production", ("completed",))
    _backfill_for_task("installation_tasks", "installation", ("completed",))
    _backfill_legacy_task_column("design_tasks", "design", ("confirmed", "completed"))
    _backfill_legacy_task_column("production_tasks", "production", ("completed",))
    _backfill_legacy_task_column("installation_tasks", "installation", ("completed",))


def downgrade() -> None:
    op.drop_index("ix_tcd_status_item_stage_time", table_name="task_item_status_logs")
    op.drop_index("ix_tcd_status_stage_time", table_name="task_item_status_logs")
    op.drop_index("ix_tcd_status_assignee_time", table_name="task_item_status_logs")
    op.drop_index("ix_tcd_status_document_item", table_name="task_item_status_logs")
    op.drop_table("task_item_status_logs")
