"""Task audit history backed by the existing operation_logs table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable
from uuid import UUID

from sqlalchemy import String, and_, exists, func, insert, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog
from app.services.operation_log_service import (
    ACTION_CREATE,
    ACTION_STATUS_CHANGE,
    ACTION_UPDATE,
)

TASK_OBJECT_TYPES = {
    "design": "design_task",
    "production": "production_task",
    "installation": "installation_task",
}
TASK_HISTORY_ACTIONS = (ACTION_CREATE, ACTION_UPDATE, ACTION_STATUS_CHANGE)
AUDITABLE_FIELDS = {
    "status",
    "progress_pct",
    "order_item_id",
    "planned_start_at",
    "planned_end_at",
    "assigned_to",
}


def _utc_now() -> datetime:
    """Return naive UTC for the existing operation-log timestamp column."""
    return datetime.now(UTC).replace(tzinfo=None)


async def _append_task_history_log(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    object_type: str,
    object_id: UUID,
    action: str,
    before_data: dict | None,
    after_data: dict,
) -> None:
    await db.execute(
        insert(OperationLog).values(
            user_id=user_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            before_data=before_data,
            after_data=after_data,
            created_at=_utc_now(),
        )
    )


def normalize_task_type(task_type: str) -> str:
    if task_type not in TASK_OBJECT_TYPES:
        raise ValueError(f"不支持的任务类型: {task_type}")
    return TASK_OBJECT_TYPES[task_type]


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def task_history_snapshot(task) -> dict:
    """Return the deliberately small, non-sensitive audit snapshot."""
    snapshot = {
        "status": task.status,
        "progress_pct": task.progress_pct,
        "planned_start_at": _serialize_value(task.planned_start_at),
        "planned_end_at": _serialize_value(task.planned_end_at),
        "assigned_to": _serialize_value(task.assigned_to),
    }
    order_item_id = getattr(task, "order_item_id", None)
    if order_item_id is not None:
        snapshot["order_item_id"] = _serialize_value(order_item_id)
    return snapshot


async def record_task_event(
    db: AsyncSession,
    task_type: str,
    task,
    action: str,
    user_id: UUID | None,
    *,
    before: dict | None = None,
    reason: str | None = None,
    changed_fields: Iterable[str] | None = None,
) -> None:
    """Append an immutable task event to the current transaction."""
    if action not in TASK_HISTORY_ACTIONS:
        raise ValueError(f"不支持的任务历史动作: {action}")

    after = task_history_snapshot(task)
    if reason:
        after["reason"] = reason
    if changed_fields:
        after["changed_fields"] = [
            field for field in changed_fields if field in AUDITABLE_FIELDS
        ]

    await _append_task_history_log(
        db,
        user_id=user_id,
        object_type=normalize_task_type(task_type),
        object_id=task.id,
        action=action,
        before_data=before,
        after_data=after,
    )


# Explicit execution-field allowlists: never return a whole order/audit snapshot.
ITEM_FIELDS = {
    "item_name": "项目内容", "material_process": "产品/材质/工艺", "specification": "规格",
    "length": "长度", "length_unit": "长度单位", "width": "宽度", "width_unit": "宽度单位",
    "height": "高度", "height_unit": "高度单位", "quantity": "数量", "unit": "单位",
    "pieces": "片数", "quantity_mode": "数量模式", "use_area": "面积计价",
    "group_name": "分项", "remark": "备注",
}
PRICE_FIELDS = {
    "unit_price": "单价", "process_fee": "工艺费", "installation_fee": "安装费",
    "design_fee": "设计费", "transport_fee": "运输费", "other_fee": "其他费用",
}
HEADER_FIELDS = {
    "project_name": "项目名称", "customer_name": "客户名称", "department": "部门/科室",
    "contact_person": "联系人", "contact_phone": "联系电话", "delivery_deadline": "交付日期",
    "installation_address": "安装地址", "remark": "订单备注", "order_date": "订单日期",
}
TASK_FIELDS = {
    "status": "任务状态", "progress_pct": "阶段进度", "planned_start_at": "计划开始",
    "planned_end_at": "计划结束", "review_required": "订单变更待复核",
}
CHANGE_TYPES = ("order_edit_batch", "order_item_add", "order_item_update", "order_item_delete", "order_date_change")


def _same_value(left, right) -> bool:
    if left == right:
        return True
    if left is None or right is None or isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def _field_changes(before: dict, after: dict, fields: dict, *, item: str | None = None) -> list[dict]:
    return [
        {"field": field, "label": label, "before": before.get(field), "after": after.get(field), "item": item}
        for field, label in fields.items()
        if not _same_value(before.get(field), after.get(field))
        and (field in before or field in after)
    ]


def order_execution_changes(snapshot: dict, item_ids: set[str], *, can_view_price: bool) -> list[dict]:
    """Compare only this task's current/historical work units, including removed items."""
    before, after = snapshot.get("before") or {}, snapshot.get("after") or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []
    changes = _field_changes(before, after, HEADER_FIELDS)
    old = {str(item.get("id")): item for item in before.get("items", []) if isinstance(item, dict)}
    new = {str(item.get("id")): item for item in after.get("items", []) if isinstance(item, dict)}
    fields = {**ITEM_FIELDS, **(PRICE_FIELDS if can_view_price else {})}
    for item_id in sorted(item_ids & (old.keys() | new.keys())):
        left, right = old.get(item_id) or {}, new.get(item_id) or {}
        label = right.get("item_name") or left.get("item_name") or "历史明细"
        left_active = bool(left) and left.get("lifecycle_status", "active") == "active"
        right_active = bool(right) and right.get("lifecycle_status", "active") == "active"
        if left_active != right_active:
            changes.append({"field": "lifecycle_status", "label": "明细范围", "item": label,
                            "before": "有效明细" if left_active else "未纳入",
                            "after": "有效明细" if right_active else "已移除"})
        changes.extend(_field_changes(left, right, fields, item=label))
    return changes


def _activity_sources(task_type, task, *, can_view_outsource: bool):
    """Union only event keys in SQL, so pagination never loads an entire audit table."""
    from app.models.business_document import BusinessDocumentVersion
    from app.models.outsource import OutsourceTask
    from app.models.task import Attachment
    from app.models.task_item_status_log import TaskItemStatusLog

    def source(model, kind, timestamp, *conditions):
        return select(model.id.label("id"), literal(kind).label("kind"), timestamp.label("occurred_at")).where(*conditions)

    material_scope = and_(
        OperationLog.object_type == "order", OperationLog.object_id == task.document_id,
        or_(
            and_(OperationLog.after_data["stage"].astext == task_type,
                 OperationLog.after_data["attachment_id"].astext.is_not(None)),
            and_(OperationLog.action == "delete", OperationLog.before_data["stage"].astext == task_type,
                 OperationLog.before_data["id"].astext.is_not(None)),
        ),
    )
    sources = [
        source(OperationLog, "operation", OperationLog.created_at,
               OperationLog.object_type == normalize_task_type(task_type), OperationLog.object_id == task.id),
        # Live item logs deliberately store naive Shanghai business time, unlike operation logs.
        source(TaskItemStatusLog, "item", TaskItemStatusLog.operated_at - literal(timedelta(hours=8)),
               TaskItemStatusLog.task_type == task_type, TaskItemStatusLog.task_id == task.id),
        source(BusinessDocumentVersion, "change", BusinessDocumentVersion.created_at,
               BusinessDocumentVersion.document_id == task.document_id,
               BusinessDocumentVersion.snapshot["change_type"].astext.in_(CHANGE_TYPES),
               BusinessDocumentVersion.created_at >= task.created_at),
        source(OperationLog, "material", OperationLog.created_at, material_scope),
        # Old uploads without an operation log still have a reliable attachment record.
        source(Attachment, "attachment", Attachment.created_at,
               Attachment.order_id == task.document_id, Attachment.stage == task_type,
               ~exists().where(OperationLog.object_type == "order", OperationLog.object_id == task.document_id,
                               OperationLog.after_data["attachment_id"].astext == Attachment.id.cast(String))),
    ]
    if can_view_outsource:
        sources.append(source(OperationLog, "outsource", OperationLog.created_at,
                              OperationLog.object_type == "outsource_task",
                              OperationLog.object_id.in_(select(OutsourceTask.id).where(
                                  OutsourceTask.related_doc_id == task.document_id,
                                  OutsourceTask.source_task_type == task_type, OutsourceTask.source_task_id == task.id))))
    return sources


async def list_task_activity(db, task_type: str, task_id: UUID, viewer, *, page=1, page_size=20, kind="all") -> dict:
    from app.core.permissions import user_has_permission
    from app.models.business_document import BusinessDocumentItem, BusinessDocumentVersion
    from app.models.task import Attachment, DesignTask, InstallationTask, ProductionTask
    from app.models.task_item_status_log import TaskItemStatusLog
    from app.models.task_order_item_link import TaskOrderItemLink
    from app.models.user import User
    from app.domain.presentation import make_outsource_status_view
    from app.services.order_task_assignment_service import get_visible_task
    from app.services.task_service import _task_status_view

    models = {"design": DesignTask, "production": ProductionTask, "installation": InstallationTask}
    normalize_task_type(task_type)
    if viewer is None or not user_has_permission(viewer, f"{task_type}_task:read"):
        raise PermissionError("没有该类型任务的查看权限")
    task = await get_visible_task(db, models[task_type], task_id, viewer)
    if task is None:
        raise ValueError("任务不存在或当前账号无权查看")
    if kind not in {"all", "change", "execution"}:
        raise ValueError("记录分类无效")
    page, page_size = max(1, page), max(1, min(page_size, 50))
    events = union_all(*_activity_sources(task_type, task, can_view_outsource=user_has_permission(viewer, "outsource_task:read"))).subquery()
    predicate = events.c.kind == "change" if kind == "change" else events.c.kind != "change" if kind == "execution" else literal(True)
    total = await db.scalar(select(func.count()).select_from(events).where(predicate))
    keys = (await db.execute(select(events).where(predicate)
                            .order_by(events.c.occurred_at.desc().nulls_last(), events.c.kind, events.c.id.desc())
                            .offset((page - 1) * page_size).limit(page_size))).all()
    if not keys:
        return {"items": [], "total": total or 0, "page": page, "page_size": page_size}

    rows = {}
    for model, kinds in ((OperationLog, {"operation", "material", "outsource"}), (TaskItemStatusLog, {"item"}),
                         (BusinessDocumentVersion, {"change"}), (Attachment, {"attachment"})):
        ids = [key.id for key in keys if key.kind in kinds]
        if ids:
            for row in (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all():
                rows[row.id] = row

    item_ids = set((await db.execute(select(TaskOrderItemLink.order_item_id).where(
        TaskOrderItemLink.task_type == task_type, TaskOrderItemLink.task_id == task.id))).scalars().all())
    if task.order_item_id:
        item_ids.add(task.order_item_id)
    item_rows = (await db.execute(select(BusinessDocumentItem).where(
        BusinessDocumentItem.document_id == task.document_id, BusinessDocumentItem.id.in_(item_ids)))).scalars().all()
    item_names = {str(row.id): row.item_name for row in item_rows}
    actor_ids = set()
    for row in rows.values():
        for field in ("user_id", "operated_by", "created_by", "uploaded_by"):
            if (value := getattr(row, field, None)) is not None:
                actor_ids.add(value)
    actors = {}
    if actor_ids:
        actors = {row.id: row.real_name or row.username for row in
                  (await db.execute(select(User).where(User.id.in_(actor_ids)))).scalars().all()}

    items = []
    for key in keys:
        row = rows.get(key.id)
        if row is None:
            continue  # A concurrent deletion must not disclose or invent an event.
        event = {"id": f"{key.kind}:{key.id}", "kind": key.kind,
                 "occurred_at": key.occurred_at.isoformat() if key.occurred_at else None,
                 "actor": None, "title": "任务记录", "detail": None, "changes": []}
        if key.kind == "change":
            snapshot = row.snapshot or {}
            event.update(title="关联订单变更", actor=actors.get(row.created_by), detail=snapshot.get("reason"),
                         batch_id=snapshot.get("change_batch_id"), version_no=row.version_no,
                         changes=order_execution_changes(snapshot, {str(value) for value in item_ids},
                                                         can_view_price=user_has_permission(viewer, "order:view_price")))
        elif key.kind == "item":
            event.update(title="明细状态变更", actor=actors.get(row.operated_by),
                         detail=item_names.get(str(row.order_item_id), "历史明细"),
                         changes=[{"field": "status", "label": "明细状态", "before": row.from_status,
                                   "after": row.to_status, "item": None}])
        elif key.kind == "attachment":
            event.update(title="上传阶段资料", actor=actors.get(row.uploaded_by), detail=row.filename)
        else:
            before, after = row.before_data or {}, row.after_data or {}
            event["actor"] = row.user_name or actors.get(row.user_id)
            if key.kind == "material":
                event.update(title="删除阶段资料" if row.action == "delete" else "上传阶段资料",
                             detail=(before if row.action == "delete" else after).get("filename"))
            elif key.kind == "outsource":
                event.update(title={"create": "发送外协", "delete": "删除外协", "status_change": "外协状态变更"}.get(row.action, "更新外协"),
                             detail=after.get("task_no"), changes=_field_changes(before, after, {"status": "外协状态"}))
            else:
                event.update(title={"create": "创建任务", "update": "更新任务", "status_change": "任务状态变更"}.get(row.action, "任务操作"),
                             detail=after.get("reason"), changes=_field_changes(before, after, TASK_FIELDS))
                if after.get("action") == "acknowledge_order_edit_review":
                    event.update(title="已复核订单变更", detail=before.get("review_reason"))
                elif after.get("action") == "historical_order_item_backfill":
                    event["title"] = "补全历史明细关联"
        for change in event["changes"]:
            if change["field"] == "status":
                for side in ("before", "after"):
                    if change[side] is not None:
                        view = (make_outsource_status_view(change[side]) if key.kind == "outsource"
                                else _task_status_view(task_type, change[side]))
                        change[side] = view.label
        items.append(event)
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}
