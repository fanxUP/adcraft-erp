from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.task_order_item_link import TaskOrderItemLink
from app.schemas.task import (
    DesignTaskResponse,
    InstallationTaskResponse,
    ProductionTaskResponse,
    TaskQueueItem,
)
from app.services.task_service import _attach_outsource_flags, _enrich_task_order
from app.services.task_schedule_service import enrich_task_dict_with_schedule_state


_TASK_SOURCES = (
    ("design", DesignTask, "design_no", DesignTaskResponse),
    ("production", ProductionTask, "production_no", ProductionTaskResponse),
    ("installation", InstallationTask, "installation_no", InstallationTaskResponse),
)


async def list_task_queue(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    stage: str | None = None,
    status: str | None = None,
    order_id: str | None = None,
    order_item_id: str | None = None,
    overdue: bool | None = None,
) -> tuple[list[dict], int]:
    """Return a normalized, paginated view over all delivery task tables."""
    normalized: list[dict] = []
    order_uuid = UUID(order_id) if order_id else None
    order_item_uuid = UUID(order_item_id) if order_item_id else None
    statuses = {value.strip() for value in (status or "").split(",") if value.strip()}

    for task_type, model, no_field, response_model in _TASK_SOURCES:
        if stage and stage != task_type:
            continue

        query = select(model)
        if order_uuid:
            query = query.where(model.document_id == order_uuid)
        if order_item_uuid:
            linked = exists().where(
                TaskOrderItemLink.task_type == task_type,
                TaskOrderItemLink.task_id == model.id,
                TaskOrderItemLink.order_item_id == order_item_uuid,
            )
            query = query.where(or_(model.order_item_id == order_item_uuid, linked))
        if statuses:
            query = query.where(model.status.in_(statuses))
        query = query.order_by(model.created_at.desc())
        tasks = list((await db.execute(query)).scalars().all())
        items: list[dict] = []
        for task in tasks:
            item = response_model.model_validate(task).model_dump(mode="json")
            item["order_id"] = item["document_id"]
            item["task_type"] = task_type
            item["stage"] = task_type
            item["task_no"] = item[no_field]
            item["_task_type"] = task_type
            item = await _enrich_task_order(db, item)
            item = enrich_task_dict_with_schedule_state(item)
            items.append(item)
        normalized.extend(await _attach_outsource_flags(db, task_type, items))

    # The project board is an active-work view. Completed, cancelled, and
    # fully-progressed aggregate tasks remain available through the stage task
    # lists and history, but do not occupy the board.
    normalized = [
        item for item in normalized
        if item.get("status") not in {"completed", "confirmed", "cancelled"}
        and int(item.get("progress_pct") or 0) < 100
    ]
    normalized.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    if overdue is not None:
        normalized = [item for item in normalized if item.get("is_overdue") is overdue]
    total = len(normalized)
    start = (page - 1) * page_size
    page_items = normalized[start:start + page_size]
    return [TaskQueueItem.model_validate(item).model_dump(mode="json") for item in page_items], total
