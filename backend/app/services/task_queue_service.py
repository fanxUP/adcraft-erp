"""Authorized SQL pagination and batched operational context for the board."""
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.access_policy import AuthorizationPolicy
from app.models.business_document import BusinessDocument, BusinessDocumentItem, OrderChangeAction
from app.models.customer import Customer
from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.task_order_item_link import TaskOrderItemLink
from app.models.user import User
from app.schemas.task import TaskQueueItem
from app.services.task_service import (
    _attach_outsource_flags, task_order_review_reason,
    task_order_review_required, add_task_contract_fields,
)
from app.services.task_schedule_service import enrich_task_dict_with_schedule_state
from app.services.order_task_assignment_service import task_visibility_clause

_TASK_SOURCES = (
    ("design", DesignTask, "design_no"),
    ("production", ProductionTask, "production_no"),
    ("installation", InstallationTask, "installation_no"),
)
_TERMINAL = {"completed", "confirmed", "cancelled", "rolled_back"}


def can_view_task_stage(task_type: str, viewer: User | None) -> bool:
    return task_type in {source[0] for source in _TASK_SOURCES} and AuthorizationPolicy(viewer).allows(f"{task_type}_task:read")


def _iso(value):
    return value.isoformat() if value else None


async def list_task_queue(
    db: AsyncSession, *, page: int, page_size: int,
    stage: str | None = None, status: str | None = None,
    order_id: str | None = None, order_item_id: str | None = None,
    overdue: bool | None = None, viewer: User | None = None,
) -> tuple[list[dict], int]:
    """Count/filter/page before loading task objects or enriching any rows."""
    if page < 1 or not 1 <= page_size <= 200:
        raise ValueError("分页参数不正确")
    queries = []
    now = datetime.now()
    statuses = [value.strip() for value in (status or "").split(",") if value.strip()]
    for task_type, model, _ in _TASK_SOURCES:
        if (stage and stage != task_type) or not can_view_task_stage(task_type, viewer):
            continue
        query = select(literal(task_type).label("stage"), model.id, model.created_at).join(
            BusinessDocument, BusinessDocument.id == model.document_id,
        ).where(
            task_visibility_clause(model, viewer), model.status.notin_(_TERMINAL),
            func.coalesce(model.progress_pct, 0) < 100,
            BusinessDocument.doc_type == "order", BusinessDocument.deleted_at.is_(None),
            BusinessDocument.status.notin_(["pending_confirm", "cancelled"]),
        )
        if order_id:
            query = query.where(model.document_id == UUID(order_id))
        if order_item_id:
            item_id = UUID(order_item_id)
            linked = exists().where(
                TaskOrderItemLink.task_type == task_type, TaskOrderItemLink.task_id == model.id,
                TaskOrderItemLink.order_item_id == item_id,
                or_(TaskOrderItemLink.item_status != "rolled_back", TaskOrderItemLink.item_status.is_(None)),
                or_(TaskOrderItemLink.link_status == "active", TaskOrderItemLink.link_status.is_(None)),
            )
            query = query.where(or_(model.order_item_id == item_id, linked))
        if statuses:
            query = query.where(model.status.in_(statuses))
        if overdue is not None:
            condition = and_(model.planned_end_at.is_not(None), model.planned_end_at < now)
            query = query.where(condition if overdue else ~condition)
        queries.append(query)
    if not queries:
        return [], 0
    candidates = union_all(*queries).subquery()
    total = await db.scalar(select(func.count()).select_from(candidates)) or 0
    page_rows = (await db.execute(select(candidates).order_by(
        candidates.c.created_at.desc(), candidates.c.stage, candidates.c.id,
    ).offset((page - 1) * page_size).limit(page_size))).all()
    if not page_rows:
        return [], total
    payloads = {}
    objects = {}
    for task_type, model, number_field in _TASK_SOURCES:
        ids = [row.id for row in page_rows if row.stage == task_type]
        if not ids:
            continue
        rows = (await db.scalars(select(model).options(raiseload("*")).where(model.id.in_(ids)))).all()
        for task in rows:
            key = (task_type, task.id)
            objects[key] = task
            payloads[key] = {
                "id": str(task.id), "task_type": task_type, "stage": task_type,
                "task_no": getattr(task, number_field), "document_id": str(task.document_id),
                "order_id": str(task.document_id), "project_name": task.project_name,
                "status": task.status, "progress_pct": task.progress_pct,
                "scope_status": task.scope_status, "review_required": task_order_review_required(task),
                "review_reason": task_order_review_reason(task),
                "is_followup": (task.scope_closed_reason or "").startswith("order_followup:"),
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                **{field: _iso(getattr(task, field)) for field in ("planned_start_at", "planned_end_at", "completed_at", "created_at", "updated_at")},
            }
    document_ids = {task.document_id for task in objects.values()}
    documents = (await db.execute(select(
        BusinessDocument.id, BusinessDocument.doc_no, BusinessDocument.project_name,
        func.coalesce(func.nullif(BusinessDocument.customer_name, ""), Customer.name).label("customer_name"),
        BusinessDocument.department, BusinessDocument.total_amount,
    ).outerjoin(Customer, Customer.id == BusinessDocument.customer_id).where(BusinessDocument.id.in_(document_ids)))).all()
    document_map = {row.id: row for row in documents}
    links = (await db.scalars(select(TaskOrderItemLink).where(or_(*[
        and_(TaskOrderItemLink.task_type == kind, TaskOrderItemLink.task_id.in_([key[1] for key in objects if key[0] == kind]))
        for kind, _, _ in _TASK_SOURCES
    ]), or_(TaskOrderItemLink.link_status == "active", TaskOrderItemLink.link_status.is_(None)))
        .order_by(TaskOrderItemLink.position, TaskOrderItemLink.id))).all()
    links_by_task = defaultdict(list)
    for link in links:
        links_by_task[(link.task_type, link.task_id)].append(link)
    item_ids = {link.order_item_id for link in links} | {task.order_item_id for task in objects.values() if task.order_item_id}
    items = (await db.scalars(select(BusinessDocumentItem).options(raiseload("*")).where(
        BusinessDocumentItem.id.in_(item_ids), BusinessDocumentItem.lifecycle_status == "active",
    ))).all() if item_ids else []
    item_map = {item.id: item for item in items}
    user_ids = {task.assigned_to for task in objects.values() if task.assigned_to} | {link.assignee_user_id for link in links if link.assignee_user_id}
    user_names = dict((await db.execute(select(User.id, User.real_name).where(User.id.in_(user_ids)))).all()) if user_ids else {}
    action_counts = {(order, module, record): count for order, module, record, count in (await db.execute(
        select(OrderChangeAction.document_id, OrderChangeAction.module, OrderChangeAction.record_key, func.count()).where(
            OrderChangeAction.document_id.in_(document_ids), OrderChangeAction.status == "pending",
            OrderChangeAction.module.in_(["execution", *[f"{kind}_{suffix}" for kind, _, _ in _TASK_SOURCES for suffix in ("tasks", "task_links")]]),
        ).group_by(OrderChangeAction.document_id, OrderChangeAction.module, OrderChangeAction.record_key))).all()}
    can_price = viewer is not None and AuthorizationPolicy(viewer).allows("order:view_price")
    for key, payload in payloads.items():
        kind, _ = key
        task = objects[key]
        doc = document_map[task.document_id]
        payload.update(order_no=doc.doc_no, project_name=doc.project_name, customer_name=doc.customer_name,
                       department=doc.department, assigned_to_name=user_names.get(task.assigned_to),
                       total_amount=float(doc.total_amount) if can_price else None)
        scope_items = []
        task_links = {link.order_item_id: link for link in links_by_task[key]}
        record_keys = {str(task.id), *[str(link.id) for link in task_links.values()], *[str(item_id) for item_id in task_links]}
        payload["pending_action_count"] = sum(count for (order, module, record), count in action_counts.items()
            if order == doc.id and module in {"execution", f"{kind}_tasks", f"{kind}_task_links"} and record in record_keys)
        ids = list(task_links)
        if task.order_item_id and task.order_item_id not in ids:
            ids.insert(0, task.order_item_id)
        for item_id in ids:
            item = item_map.get(item_id)
            if not item:
                continue
            link = task_links.get(item_id)
            snapshot = (link.scope_snapshot or {}) if link else {}
            scope_items.append({"order_item_id": str(item_id), "item_name": item.item_name,
                "current_quantity": float(item.quantity), "unit": item.unit,
                "planned_quantity": float(link.planned_quantity) if link and link.planned_quantity is not None else None,
                "completed_quantity": float(link.completed_quantity) if link and link.completed_quantity is not None else None,
                "scope_item_name": snapshot.get("item_name"), "scope_unit": snapshot.get("unit"),
                "assignee_name": user_names.get(link.assignee_user_id) if link else None})
        payload["is_followup"] = payload["is_followup"] or any((link.scope_snapshot or {}).get("task_origin") == "order_followup" for link in task_links.values())
        payload.update(scope_items=scope_items, order_item_ids=[row["order_item_id"] for row in scope_items],
                       item_names=[row["item_name"] for row in scope_items])
        enrich_task_dict_with_schedule_state(payload, now=now)
        add_task_contract_fields(payload, kind)
    for kind, _, _ in _TASK_SOURCES:
        await _attach_outsource_flags(db, kind, [value for key, value in payloads.items() if key[0] == kind], viewer=viewer)
    return [TaskQueueItem.model_validate(payloads[(row.stage, row.id)]).model_dump(mode="json") for row in page_rows], total
