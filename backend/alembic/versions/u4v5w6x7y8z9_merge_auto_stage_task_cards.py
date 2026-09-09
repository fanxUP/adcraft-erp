"""Merge legacy per-item automatic task cards into one stage card.

The old automatic task creator generated one pending task row for every
active order item. This migration only merges rows that still match that
unmodified automatic shape. It preserves task history and attachments by
retargeting polymorphic references to the oldest task before removing the
duplicate rows.

Production rollout requirement: take a database backup before applying this
revision. The downgrade intentionally refuses to run because restoring
deleted duplicate rows requires the pre-migration backup.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, None] = "t3u4v5w6x7y8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TASK_SPECS = (
    (
        "design",
        "design_tasks",
        "design_no",
        "design_task",
        ("description", "design_file_url", "client_comments"),
    ),
    (
        "production",
        "production_tasks",
        "production_no",
        "production_task",
        ("qc_result", "rework_reason"),
    ),
    (
        "installation",
        "installation_tasks",
        "installation_no",
        "installation_task",
        ("acceptance_result", "scheduled_at"),
    ),
)

_INSTALLATION_REFERENCE_TABLES = (
    "vehicle_use_requests",
    "vehicle_dispatches",
    "vehicle_incidents",
    "vehicle_cost_allocations",
)


def _legacy_auto_split_rows(
    bind,
    task_type: str,
    table_name: str,
    number_field: str,
    custom_fields: tuple[str, ...],
):
    fields = ", ".join(f"t.{field}" for field in custom_fields)
    custom_select = f", {fields}" if fields else ""
    rows = bind.execute(
        sa.text(
            f"""
            SELECT
                t.id,
                t.{number_field} AS task_no,
                t.document_id,
                t.order_item_id,
                t.status,
                t.progress_pct,
                t.completed_at,
                t.created_at,
                t.assigned_to,
                t.planned_start_at,
                t.planned_end_at,
                t.project_name,
                d.project_name AS document_project_name
                {custom_select}
            FROM {table_name} AS t
            JOIN business_documents AS d ON d.id = t.document_id
            WHERE t.status = 'pending'
              AND t.order_item_id IS NOT NULL
              AND t.project_name = d.project_name
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_order_item_links AS link
                  WHERE link.task_type = :task_type
                    AND link.task_id = t.id
              )
            ORDER BY t.document_id, t.created_at, t.{number_field}, t.id
            """
        ),
        {"task_type": task_type},
    ).mappings().all()

    groups = defaultdict(list)
    for row in rows:
        if any(row[field] is not None for field in custom_fields):
            continue
        if row["assigned_to"] is not None:
            continue
        if row["planned_start_at"] is not None or row["planned_end_at"] is not None:
            continue
        groups[row["document_id"]].append(row)
    return groups


def _move_polymorphic_references(bind, task_type: str, duplicate_id, canonical_id) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE attachments
            SET related_id = :canonical_id
            WHERE related_type = :related_type
              AND related_id = :duplicate_id
            """
        ),
        {
            "canonical_id": canonical_id,
            "duplicate_id": duplicate_id,
            "related_type": f"{task_type}_task",
        },
    )
    bind.execute(
        sa.text(
            """
            UPDATE operation_logs
            SET object_id = :canonical_id
            WHERE object_type = :object_type
              AND object_id = :duplicate_id
            """
        ),
        {
            "canonical_id": canonical_id,
            "duplicate_id": duplicate_id,
            "object_type": f"{task_type}_task",
        },
    )
    bind.execute(
        sa.text(
            """
            UPDATE outsource_tasks
            SET source_task_id = :canonical_id
            WHERE source_task_type = :task_type
              AND source_task_id = :duplicate_id
            """
        ),
        {
            "canonical_id": canonical_id,
            "duplicate_id": duplicate_id,
            "task_type": task_type,
        },
    )

    if task_type == "installation":
        for table_name in _INSTALLATION_REFERENCE_TABLES:
            bind.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                    SET related_install_task_id = :canonical_id
                    WHERE related_install_task_id = :duplicate_id
                    """
                ),
                {
                    "canonical_id": canonical_id,
                    "duplicate_id": duplicate_id,
                },
            )


def _merge_group(bind, task_type: str, table_name: str, rows: list[dict]) -> None:
    if len(rows) < 2:
        return

    item_ids = [row["order_item_id"] for row in rows]
    if len(set(item_ids)) != len(item_ids):
        # Duplicate rows for the same detail are not the known automatic
        # split shape; leave them for an explicit manual repair.
        return

    canonical_id = rows[0]["id"]
    for position, row in enumerate(rows):
        bind.execute(
            sa.text(
                """
                INSERT INTO task_order_item_links (
                    task_type,
                    task_id,
                    order_item_id,
                    position,
                    item_status,
                    item_progress_pct,
                    item_completed_at
                )
                VALUES (
                    :task_type,
                    :task_id,
                    :order_item_id,
                    :position,
                    :item_status,
                    :item_progress_pct,
                    :item_completed_at
                )
                ON CONFLICT (task_type, task_id, order_item_id) DO NOTHING
                """
            ),
            {
                "task_type": task_type,
                "task_id": canonical_id,
                "order_item_id": row["order_item_id"],
                "position": position,
                "item_status": row["status"],
                "item_progress_pct": row["progress_pct"],
                "item_completed_at": row["completed_at"],
            },
        )

    # The many-link rows now carry the full scope. Null the legacy singular
    # column so later code cannot accidentally treat the card as one-item.
    bind.execute(
        sa.text(f"UPDATE {table_name} SET order_item_id = NULL WHERE id = :task_id"),
        {"task_id": canonical_id},
    )

    for row in rows[1:]:
        duplicate_id = row["id"]
        _move_polymorphic_references(bind, task_type, duplicate_id, canonical_id)
        bind.execute(
            sa.text(
                """
                DELETE FROM task_order_item_links
                WHERE task_type = :task_type
                  AND task_id = :task_id
                """
            ),
            {"task_type": task_type, "task_id": duplicate_id},
        )
        bind.execute(
            sa.text(f"DELETE FROM {table_name} WHERE id = :task_id"),
            {"task_id": duplicate_id},
        )


def _backfill_legacy_links(bind, task_type: str, table_name: str) -> None:
    bind.execute(
        sa.text(
            f"""
            INSERT INTO task_order_item_links (
                task_type,
                task_id,
                order_item_id,
                position,
                item_status,
                item_progress_pct,
                item_completed_at
            )
            SELECT
                :task_type,
                t.id,
                t.order_item_id,
                0,
                t.status,
                t.progress_pct,
                t.completed_at
            FROM {table_name} AS t
            WHERE t.order_item_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_order_item_links AS link
                  WHERE link.task_type = :task_type
                    AND link.task_id = t.id
                    AND link.order_item_id = t.order_item_id
              )
            """
        ),
        {"task_type": task_type},
    )


def upgrade() -> None:
    bind = op.get_bind()
    for task_type, table_name, number_field, _object_type, custom_fields in _TASK_SPECS:
        groups = _legacy_auto_split_rows(
            bind,
            task_type,
            table_name,
            number_field,
            custom_fields,
        )
        for rows in groups.values():
            _merge_group(bind, task_type, table_name, rows)

    # Compatibility for tasks created before the many-link table was used.
    for task_type, table_name, _number_field, _object_type, _custom_fields in _TASK_SPECS:
        _backfill_legacy_links(bind, task_type, table_name)


def downgrade() -> None:
    raise RuntimeError(
        "u4v5w6x7y8z9 合并了旧任务卡并删除了重复行，不能自动降级；请使用迁移前数据库备份恢复"
    )
