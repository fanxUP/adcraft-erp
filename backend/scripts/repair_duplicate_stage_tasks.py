"""Merge duplicate automatic stage task cards without losing work history.

The automatic delivery workflow is intended to have one card per order and
stage. Older releases could create another card when a previously completed
batch was followed by more order items entering the same stage. This utility
repairs those historical rows explicitly; it never runs as part of normal
application startup or deployment.

Safety model:

* dry-run is the default and rolls back its read transaction;
* ``--apply`` must be paired with a document id or the explicit ``--all``;
* the caller must take a database backup before ``--apply``;
* duplicate task rows are merged into the oldest automatic card with linked
  work (falling back to the oldest empty card only when no work is linked), then removed
  only after attachments, audit events, item events, outsource references and
  vehicle references have been retargeted;
* the operation is one transaction, so a failed apply rolls back completely.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine


TASK_SPECS: dict[str, dict[str, Any]] = {
    "design": {
        "table": "design_tasks",
        "number_field": "design_no",
        "completed_status": "confirmed",
        "terminal_statuses": {"confirmed", "completed", "cancelled"},
        "status_priority": {"pending": 0, "revision": 1, "designing": 2, "pending_review": 3},
        "preserve_fields": (
            "assigned_to",
            "planned_start_at",
            "planned_end_at",
            "description",
            "design_file_url",
            "client_comments",
        ),
    },
    "production": {
        "table": "production_tasks",
        "number_field": "production_no",
        "completed_status": "completed",
        "terminal_statuses": {"completed", "cancelled"},
        "status_priority": {"pending": 0, "rework": 1, "in_progress": 2},
        "preserve_fields": (
            "assigned_to",
            "planned_start_at",
            "planned_end_at",
            "material_id",
            "process_id",
            "length",
            "width",
            "height",
            "quantity",
            "qc_result",
            "rework_reason",
        ),
    },
    "installation": {
        "table": "installation_tasks",
        "number_field": "installation_no",
        "completed_status": "completed",
        "terminal_statuses": {"completed", "cancelled"},
        "status_priority": {
            "pending": 0,
            "assigned": 1,
            "in_progress": 2,
            "pending_acceptance": 3,
        },
        "preserve_fields": (
            "assigned_to",
            "planned_start_at",
            "planned_end_at",
            "address",
            "contact_name",
            "contact_phone",
            "scheduled_at",
            "acceptance_result",
        ),
    },
}

VEHICLE_REFERENCE_TABLES = (
    "vehicle_use_requests",
    "vehicle_dispatches",
    "vehicle_incidents",
    "vehicle_cost_allocations",
)


@dataclass(frozen=True)
class MergePlan:
    task_type: str
    document_id: UUID
    canonical: dict[str, Any]
    duplicates: tuple[dict[str, Any], ...]
    merged_links: tuple[dict[str, Any], ...]
    aggregate_status: str
    aggregate_progress: int
    aggregate_completed_at: datetime | None


def _uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _link_is_terminal(task_type: str, status: str | None) -> bool:
    return status in TASK_SPECS[task_type]["terminal_statuses"]


def _link_progress(row: dict[str, Any]) -> int:
    value = row.get("item_progress_pct")
    try:
        return max(0, min(100, int(value))) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _prefer_link(task_type: str, current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Choose the most complete state, preserving the earliest completion."""
    current_terminal = _link_is_terminal(task_type, current.get("item_status"))
    candidate_terminal = _link_is_terminal(task_type, candidate.get("item_status"))
    if candidate_terminal != current_terminal:
        return candidate if candidate_terminal else current

    current_time = current.get("item_completed_at")
    candidate_time = candidate.get("item_completed_at")
    if (candidate_time is not None) != (current_time is not None):
        return candidate if candidate_time is not None else current
    if candidate_time is not None and current_time is not None and candidate_time != current_time:
        return candidate if candidate_time < current_time else current

    current_progress = _link_progress(current)
    candidate_progress = _link_progress(candidate)
    if candidate_progress != current_progress:
        return candidate if candidate_progress > current_progress else current

    if current.get("assignee_user_id") is None and candidate.get("assignee_user_id") is not None:
        return candidate
    return current


def _aggregate_status(task_type: str, statuses: list[str]) -> str:
    if not statuses:
        return "pending"
    terminal_statuses = TASK_SPECS[task_type]["terminal_statuses"]
    completed_statuses = terminal_statuses - {"cancelled"}
    if all(status in completed_statuses for status in statuses):
        return TASK_SPECS[task_type]["completed_status"]
    if all(status in terminal_statuses for status in statuses):
        return "cancelled"
    priority = TASK_SPECS[task_type]["status_priority"]
    return max(statuses, key=lambda status: priority.get(status, 0))


def build_merge_plan(
    task_type: str,
    tasks: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> MergePlan | None:
    """Build a deterministic plan from already-read database rows."""
    if len(tasks) < 2:
        return None

    ordered_tasks = sorted(
        tasks,
        key=lambda row: (row.get("created_at") or datetime.max, str(row["id"])),
    )
    task_rank = {str(row["id"]): index for index, row in enumerate(ordered_tasks)}
    ordered_links = sorted(
        links,
        key=lambda row: (
            task_rank.get(str(row["task_id"]), len(task_rank)),
            int(row.get("position") or 0),
            str(row["order_item_id"]),
        ),
    )
    task_ids_with_links = {str(row["task_id"]) for row in ordered_links}
    canonical = next(
        (row for row in ordered_tasks if str(row["id"]) in task_ids_with_links),
        ordered_tasks[0],
    )
    duplicates = tuple(
        row for row in ordered_tasks if str(row["id"]) != str(canonical["id"])
    )

    by_item: dict[str, list[dict[str, Any]]] = {}
    selected: dict[str, dict[str, Any]] = {}
    first_position: dict[str, int] = {}
    for row in ordered_links:
        item_key = str(row["order_item_id"])
        by_item.setdefault(item_key, []).append(row)
        first_position.setdefault(item_key, len(first_position))
        current = selected.get(item_key)
        selected[item_key] = row if current is None else _prefer_link(task_type, current, row)

    merged_links: list[dict[str, Any]] = []
    for item_key, row in sorted(selected.items(), key=lambda pair: first_position[pair[0]]):
        merged = dict(row)
        if merged.get("assignee_user_id") is None:
            merged["assignee_user_id"] = next(
                (
                    candidate.get("assignee_user_id")
                    for candidate in by_item[item_key]
                    if candidate.get("assignee_user_id") is not None
                ),
                None,
            )
        merged["position"] = len(merged_links)
        merged_links.append(merged)

    statuses = [str(row.get("item_status") or "pending") for row in merged_links]
    aggregate_status = _aggregate_status(task_type, statuses)
    aggregate_progress = round(sum(_link_progress(row) for row in merged_links) / len(merged_links)) if merged_links else 0
    if aggregate_status in TASK_SPECS[task_type]["terminal_statuses"] - {"cancelled"}:
        timestamps = [row.get("item_completed_at") for row in merged_links if row.get("item_completed_at") is not None]
        timestamps.extend(
            row.get("completed_at")
            for row in ordered_tasks
            if row.get("completed_at") is not None
        )
        aggregate_completed_at = max(timestamps) if timestamps else None
    else:
        aggregate_completed_at = None

    return MergePlan(
        task_type=task_type,
        document_id=_uuid(canonical["document_id"]),
        canonical=canonical,
        duplicates=duplicates,
        merged_links=tuple(merged_links),
        aggregate_status=aggregate_status,
        aggregate_progress=aggregate_progress,
        aggregate_completed_at=aggregate_completed_at,
    )


def _format_plan(plan: MergePlan) -> str:
    duplicate_nos = "、".join(str(row["task_no"]) for row in plan.duplicates)
    duplicate_ids = "、".join(str(row["id"]) for row in plan.duplicates)
    return (
        f"[{plan.task_type}] 订单 {plan.document_id}: 保留 {plan.canonical['task_no']} "
        f"({plan.canonical['id']})，合并 {duplicate_nos} ({duplicate_ids})；"
        f"合并后 {len(plan.merged_links)} 条明细，状态 {plan.aggregate_status}，"
        f"进度 {plan.aggregate_progress}%"
    )


async def _load_plans(
    conn: AsyncConnection,
    task_type: str,
    document_id: UUID | None,
    *,
    lock_rows: bool,
) -> list[MergePlan]:
    spec = TASK_SPECS[task_type]
    table = spec["table"]
    preserve_columns = ", ".join(f"t.{field}" for field in spec["preserve_fields"])
    document_clause = "AND t.document_id = :document_id" if document_id else ""
    lock_clause = " FOR UPDATE" if lock_rows else ""
    task_rows = (
        await conn.execute(
            text(
                f"""
                SELECT t.id, t.{spec['number_field']} AS task_no,
                       t.document_id, t.status, t.progress_pct,
                       t.created_at, t.updated_at, t.completed_at,
                       t.order_item_id, {preserve_columns}
                FROM {table} t
                WHERE t.status <> :cancelled
                  AND t.order_item_id IS NULL
                  {document_clause}
                ORDER BY t.document_id, t.created_at, t.id
                {lock_clause}
                """
            ),
            {"cancelled": "cancelled", **({"document_id": document_id} if document_id else {})},
        )
    ).mappings().all()
    tasks_by_document: dict[UUID, list[dict[str, Any]]] = {}
    for row in task_rows:
        tasks_by_document.setdefault(_uuid(row["document_id"]), []).append(dict(row))

    if not tasks_by_document:
        return []

    links_result = await conn.execute(
        text(
            f"""
            SELECT l.task_id, l.order_item_id, l.position,
                   l.assignee_user_id, l.item_status,
                   l.item_progress_pct, l.item_completed_at
            FROM task_order_item_links l
            JOIN {table} t ON t.id = l.task_id
            WHERE l.task_type = :task_type
              AND t.status <> :cancelled
              AND t.order_item_id IS NULL
              {document_clause}
            ORDER BY t.document_id, t.created_at, t.id, l.position, l.order_item_id
            """
        ),
        {
            "task_type": task_type,
            "cancelled": "cancelled",
            **({"document_id": document_id} if document_id else {}),
        },
    )
    links_by_document: dict[UUID, list[dict[str, Any]]] = {}
    task_to_document = {
        str(row["id"]): document_key
        for document_key, rows in tasks_by_document.items()
        for row in rows
    }
    for row in links_result.mappings().all():
        document_key = task_to_document.get(str(row["task_id"]))
        if document_key is not None:
            links_by_document.setdefault(document_key, []).append(dict(row))

    plans: list[MergePlan] = []
    for document_key, rows in tasks_by_document.items():
        plan = build_merge_plan(task_type, rows, links_by_document.get(document_key, []))
        if plan is not None and plan.merged_links:
            plans.append(plan)
    return plans


async def _merge_plan(conn: AsyncConnection, plan: MergePlan) -> None:
    spec = TASK_SPECS[plan.task_type]
    table = spec["table"]
    canonical_id = _uuid(plan.canonical["id"])
    duplicate_ids = [_uuid(row["id"]) for row in plan.duplicates]

    for field in spec["preserve_fields"]:
        if plan.canonical.get(field) is not None:
            continue
        fallback = next((row.get(field) for row in plan.duplicates if row.get(field) is not None), None)
        if fallback is not None:
            await conn.execute(
                text(f"UPDATE {table} SET {field} = :value WHERE id = :task_id"),
                {"value": fallback, "task_id": canonical_id},
            )

    canonical_links = (
        await conn.execute(
            text(
                """
                SELECT order_item_id
                FROM task_order_item_links
                WHERE task_type = :task_type AND task_id = :task_id
                """
            ),
            {"task_type": plan.task_type, "task_id": canonical_id},
        )
    ).scalars().all()
    canonical_item_ids = {_uuid(value) for value in canonical_links}

    for row in plan.merged_links:
        params = {
            "task_type": plan.task_type,
            "task_id": canonical_id,
            "order_item_id": _uuid(row["order_item_id"]),
            "assignee_user_id": row.get("assignee_user_id"),
            "position": int(row["position"]),
            "item_status": row.get("item_status"),
            "item_progress_pct": _link_progress(row),
            "item_completed_at": row.get("item_completed_at"),
        }
        if params["order_item_id"] in canonical_item_ids:
            await conn.execute(
                text(
                    """
                    UPDATE task_order_item_links
                    SET assignee_user_id = :assignee_user_id,
                        position = :position,
                        item_status = :item_status,
                        item_progress_pct = :item_progress_pct,
                        item_completed_at = :item_completed_at
                    WHERE task_type = :task_type
                      AND task_id = :task_id
                      AND order_item_id = :order_item_id
                    """
                ),
                params,
            )
        else:
            await conn.execute(
                text(
                    """
                    INSERT INTO task_order_item_links
                        (task_type, task_id, order_item_id, assignee_user_id,
                         position, item_status, item_progress_pct, item_completed_at)
                    VALUES
                        (:task_type, :task_id, :order_item_id, :assignee_user_id,
                         :position, :item_status, :item_progress_pct, :item_completed_at)
                    """
                ),
                params,
            )

    await conn.execute(
        text(
            f"""
            UPDATE {table}
            SET order_item_id = NULL,
                status = :status,
                progress_pct = :progress_pct,
                completed_at = :completed_at,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :task_id
            """
        ),
        {
            "status": plan.aggregate_status,
            "progress_pct": plan.aggregate_progress,
            "completed_at": plan.aggregate_completed_at,
            "task_id": canonical_id,
        },
    )

    for duplicate_id in duplicate_ids:
        await conn.execute(
            text(
                """
                UPDATE attachments
                SET related_id = :canonical_id
                WHERE related_type = :related_type AND related_id = :duplicate_id
                """
            ),
            {
                "related_type": f"{plan.task_type}_task",
                "canonical_id": canonical_id,
                "duplicate_id": duplicate_id,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE operation_logs
                SET object_id = :canonical_id
                WHERE object_type = :object_type AND object_id = :duplicate_id
                """
            ),
            {
                "object_type": f"{plan.task_type}_task",
                "canonical_id": canonical_id,
                "duplicate_id": duplicate_id,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE task_item_status_logs
                SET task_id = :canonical_id
                WHERE task_type = :task_type AND task_id = :duplicate_id
                """
            ),
            {
                "task_type": plan.task_type,
                "canonical_id": canonical_id,
                "duplicate_id": duplicate_id,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE outsource_tasks
                SET source_task_id = :canonical_id
                WHERE source_task_type = :task_type AND source_task_id = :duplicate_id
                """
            ),
            {
                "task_type": plan.task_type,
                "canonical_id": canonical_id,
                "duplicate_id": duplicate_id,
            },
        )
        if plan.task_type == "installation":
            for table_name in VEHICLE_REFERENCE_TABLES:
                await conn.execute(
                    text(
                        f"""
                        UPDATE {table_name}
                        SET related_install_task_id = :canonical_id
                        WHERE related_install_task_id = :duplicate_id
                        """
                    ),
                    {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
                )

        await conn.execute(
            text(
                """
                DELETE FROM task_order_item_links
                WHERE task_type = :task_type AND task_id = :task_id
                """
            ),
            {"task_type": plan.task_type, "task_id": duplicate_id},
        )
        await conn.execute(
            text(f"DELETE FROM {table} WHERE id = :task_id"),
            {"task_id": duplicate_id},
        )

    merge_log = {
        "reason": "合并重复的自动阶段任务卡",
        "merged_task_nos": [str(row["task_no"]) for row in plan.duplicates],
        "merged_task_ids": [str(row["id"]) for row in plan.duplicates],
        "linked_item_count": len(plan.merged_links),
        "status": plan.aggregate_status,
        "progress_pct": plan.aggregate_progress,
    }
    await conn.execute(
        text(
            """
            INSERT INTO operation_logs
                (id, object_type, object_id, action, after_data, created_at)
            VALUES
                (:id, :object_type, :object_id, :action,
                 CAST(:after_data AS jsonb), CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": uuid4(),
            "object_type": f"{plan.task_type}_task",
            "object_id": canonical_id,
            "action": "update",
            "after_data": json.dumps(merge_log, ensure_ascii=False),
        },
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="合并重复的自动阶段任务卡")
    parser.add_argument("--task-type", choices=tuple(TASK_SPECS), default="installation")
    parser.add_argument("--document-id", help="只修复指定订单/项目 UUID")
    parser.add_argument("--all", action="store_true", help="扫描指定阶段的全部订单；必须显式指定")
    parser.add_argument("--backup-reference", help="执行修复前已完成的数据库备份文件路径")
    parser.add_argument("--apply", action="store_true", help="提交修复；默认只预览并回滚")
    args = parser.parse_args()
    if args.document_id and args.all:
        parser.error("--document-id 与 --all 不能同时使用")
    if args.apply and not args.document_id and not args.all:
        parser.error("执行修复时必须指定 --document-id 或显式使用 --all")
    if args.apply and not args.backup_reference:
        parser.error("执行修复前必须提供 --backup-reference")
    if args.document_id:
        try:
            args.document_id = UUID(args.document_id)
        except ValueError as exc:
            parser.error(f"document-id 不是有效 UUID：{exc}")
    return args


async def _run(args: argparse.Namespace) -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("请通过环境变量 DATABASE_URL 提供数据库连接")
    if args.apply and not Path(args.backup_reference).is_file():
        raise RuntimeError(f"备份文件不存在，已停止修复：{args.backup_reference}")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            if args.apply and args.document_id:
                await conn.execute(
                    text(
                        "SELECT id FROM business_documents WHERE id = :document_id FOR UPDATE"
                    ),
                    {"document_id": args.document_id},
                )
            plans = await _load_plans(
                conn,
                args.task_type,
                args.document_id,
                lock_rows=args.apply,
            )
            if not plans:
                print("未发现符合条件的重复自动任务卡。")
            else:
                for plan in plans:
                    print(_format_plan(plan))
            if args.apply:
                for plan in plans:
                    await _merge_plan(conn, plan)
                await transaction.commit()
                print(f"已提交 {len(plans)} 组任务卡合并。")
            else:
                await transaction.rollback()
                print("当前为预览模式，未写入数据库。")
        except Exception:
            await transaction.rollback()
            raise
    await engine.dispose()
    return 0


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
