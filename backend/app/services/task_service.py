import inspect
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflows import (
    DESIGN_TASK_WORKFLOW,
    INSTALLATION_TASK_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
)
from app.domain.presentation import make_action_capability, make_status_view
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.customer import Customer  # noqa: F401  # register BusinessDocument.customer
from app.models.task_item_status_log import TaskItemStatusLog
from app.models.task_order_item_link import TaskOrderItemLink
from app.models.user import User
from app.models.vehicle import Vehicle  # noqa: F401  # register Attachment.vehicle
from app.core.permissions import (
    ORDER_ITEM_PRICE_FIELDS,
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_INSTALLATION_TASK_CHANGE_STATUS,
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_ORDER_VIEW_PRICE,
    PERM_OUTSOURCE_TASK_READ,
    PERM_PRODUCTION_TASK_CHANGE_STATUS,
    user_has_permission,
)
from app.repositories.task_repo import (
    AttachmentRepository,
    DesignTaskRepository,
    InstallationTaskRepository,
    ProductionTaskRepository,
)
from app.schemas.attachment import AttachmentResponse
from app.schemas.order import OrderItemResponse
from app.schemas.task import (
    DesignTaskResponse,
    InstallationTaskResponse,
    ProductionTaskResponse,
    TaskOrderItemOption,
)
from app.services.number_generator import (
    generate_design_no,
    generate_installation_no,
    generate_production_no,
)
from app.services.operation_log_service import (
    ACTION_CREATE,
    ACTION_STATUS_CHANGE,
    ACTION_UPDATE,
)
from app.services.task_history_service import record_task_event, task_history_snapshot
from app.services.task_schedule_service import (
    enrich_task_dict_with_schedule_state,
    normalize_task_schedule_data,
)
from app.services.order_task_assignment_service import (
    can_assign_task,
    get_visible_task,
    resolve_current_employee_user_id,
    validate_task_assignee,
)

ACTIVE_ORDER_STATUSES = ("designing", "in_production", "in_installation")

ORDER_ITEM_STAGE_LABELS = {
    "designing": "设计中",
    "in_production": "制作中",
    "in_installation": "安装中",
    "completed": "已完成",
    "not_ready": "未就绪",
}
TASK_TYPE_STAGES = {
    "design": "designing",
    "production": "in_production",
    "installation": "in_installation",
}
TASK_TYPE_LABELS = {
    "design": "设计",
    "production": "制作",
    "installation": "安装",
}
TASK_CHANGE_PERMISSION_BY_TYPE = {
    "design": PERM_DESIGN_TASK_CHANGE_STATUS,
    "production": PERM_PRODUCTION_TASK_CHANGE_STATUS,
    "installation": PERM_INSTALLATION_TASK_CHANGE_STATUS,
}

DESIGN_IN_PROGRESS_STATUSES = {
    "pending",
    "designing",
    "pending_review",
    "revision",
}
DESIGN_COMPLETED_STATUSES = {"confirmed", "completed"}
PRODUCTION_IN_PROGRESS_STATUSES = {"pending", "in_progress", "rework"}
PRODUCTION_COMPLETED_STATUSES = {"completed"}
INSTALLATION_IN_PROGRESS_STATUSES = {
    "pending",
    "assigned",
    "in_progress",
    "pending_acceptance",
}
INSTALLATION_COMPLETED_STATUSES = {"completed"}
TASK_CANCELLED_STATUS = "cancelled"
TASK_RELEASE_STATUSES = {
    "design": {"pending"},
    "production": {"pending"},
    "installation": {"pending"},
}


def _utc_now() -> datetime:
    """Return naive UTC for the existing task timestamp columns."""
    return datetime.now(UTC).replace(tzinfo=None)


_BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _business_now_naive() -> datetime:
    """Return Shanghai business time for completion event history."""
    return datetime.now(_BUSINESS_TIMEZONE).replace(tzinfo=None)

TASK_STATUS_PROGRESS = {
    "design": {
        "pending": 0,
        "designing": 50,
        "pending_review": 60,
        "revision": 40,
        "confirmed": 100,
        "completed": 100,
        "cancelled": 100,
    },
    "production": {
        "pending": 0,
        "in_progress": 50,
        "rework": 30,
        "completed": 100,
        "cancelled": 100,
    },
    "installation": {
        "pending": 0,
        "assigned": 25,
        "in_progress": 50,
        "pending_acceptance": 75,
        "completed": 100,
        "cancelled": 100,
    },
}

TASK_STATUS_LABELS = {
    "design": {
        "pending": "待分配",
        "designing": "设计中",
        "pending_review": "待处理",
        "revision": "需修改",
        "confirmed": "已完成",
        "completed": "已完成",
        "cancelled": "已取消",
    },
    "production": {
        "pending": "待制作",
        "in_progress": "制作中",
        "rework": "返工",
        "completed": "已完成",
        "cancelled": "已取消",
    },
    "installation": {
        "pending": "待分配",
        "assigned": "已分配",
        "in_progress": "安装中",
        "pending_acceptance": "待处理",
        "completed": "已完成",
        "cancelled": "已取消",
    },
}

TASK_COMPLETED_STATUSES = {
    "design": {"confirmed", "completed"},
    "production": {"completed"},
    "installation": {"completed"},
}

TASK_TERMINAL_STATUSES = {
    task_type: statuses | {TASK_CANCELLED_STATUS}
    for task_type, statuses in TASK_COMPLETED_STATUSES.items()
}

OUTSOURCE_BLOCKING_TASK_TYPES = frozenset({"production", "installation"})
OUTSOURCE_BLOCKING_STATUSES = frozenset({"pending", "in_progress"})
OUTSOURCE_BLOCKING_STATUS_LABELS = {
    "pending": "外协待处理",
    "in_progress": "外协任务进行中",
}


def can_view_outsource_tasks(viewer: User | None) -> bool:
    """Return whether a task response may disclose external-work metadata.

    Internal callers without a viewer retain the existing full-data behavior.
    Authenticated callers must hold the explicit external-task read permission;
    task-module permissions alone never imply visibility of outsourcing.
    """

    return viewer is None or user_has_permission(viewer, PERM_OUTSOURCE_TASK_READ)


def visible_outsource_fields(viewer: User | None, outsource: dict) -> dict:
    """Return only external-task fields the current viewer may receive."""

    if can_view_outsource_tasks(viewer):
        return outsource
    return {
        "outsource_blocked": False,
        "outsource_status": None,
        "outsource_status_label": None,
        "outsource_task_count": 0,
        "outsource_task_nos": [],
    }


def _item_status_progress(task_type: str, status: str, fallback: int = 0) -> int:
    return int(TASK_STATUS_PROGRESS.get(task_type, {}).get(status, fallback))


def _item_status_label(task_type: str, status: str | None) -> str | None:
    return TASK_STATUS_LABELS.get(task_type, {}).get(status) if status else None


def _task_status_view(task_type: str, status: str | None):
    normalized = status or "unknown"
    return make_status_view(
        normalized,
        _item_status_label(task_type, normalized),
        terminal=normalized in TASK_TERMINAL_STATUSES.get(task_type, set()),
    )


def _task_capabilities(task_type: str, status: str | None) -> dict:
    normalized = status or "unknown"
    terminal = normalized in TASK_TERMINAL_STATUSES.get(task_type, set())
    return {
        "change_status": make_action_capability(
            not terminal,
            "任务已完成或已取消，不能继续变更状态" if terminal else None,
        ).model_dump(mode="json"),
    }


def add_task_contract_fields(task_dict: dict, task_type: str) -> dict:
    """Add canonical status and object-state capabilities to a task payload."""
    status = task_dict.get("status")
    task_dict["status_view"] = _task_status_view(task_type, status).model_dump(mode="json")
    task_dict["capabilities"] = _task_capabilities(task_type, status)
    return task_dict


def _is_completed_item_status(task_type: str, status: str) -> bool:
    return status in TASK_COMPLETED_STATUSES.get(task_type, set())


def _is_terminal_item_status(task_type: str, status: str) -> bool:
    return status in TASK_TERMINAL_STATUSES.get(task_type, set())


def _coerce_uuid(value) -> UUID | None:
    """Return a UUID for real model values, ignoring loose test/magic values."""
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def _task_order_item_id(task) -> UUID | None:
    return _coerce_uuid(getattr(task, "order_item_id", None))


async def _blocking_outsource_map(
    db: AsyncSession,
    document_id: UUID,
    task_type: str,
    item_ids: list[UUID] | set[UUID],
) -> dict[UUID, dict]:
    """Return active item-level outsource work that still blocks progression.

    External work is scoped by order, item, and the current production stage.
    Order-level outsource tasks intentionally do not get guessed onto items.
    """
    if task_type not in OUTSOURCE_BLOCKING_TASK_TYPES:
        return {}

    normalized_item_ids = {
        item_id
        for raw_item_id in item_ids
        if (item_id := _coerce_uuid(raw_item_id)) is not None
    }
    if not normalized_item_ids:
        return {}

    from app.models.outsource import OutsourceTask

    result = await db.execute(
        select(OutsourceTask).where(
            OutsourceTask.related_doc_id == document_id,
            OutsourceTask.related_doc_type == "order",
            OutsourceTask.order_item_id.in_(normalized_item_ids),
            OutsourceTask.task_type == task_type,
            OutsourceTask.status.in_(OUTSOURCE_BLOCKING_STATUSES),
            OutsourceTask.deleted_at.is_(None),
        )
    )
    try:
        scalars = result.scalars()
        if inspect.isawaitable(scalars):
            scalars = await scalars
        values = scalars.all()
        if inspect.isawaitable(values):
            values = await values
        tasks = list(values)
    except AttributeError:
        tasks = []

    blocked: dict[UUID, dict] = {}
    status_priority = {"pending": 1, "in_progress": 2}
    for outsource_task in tasks:
        item_id = _coerce_uuid(getattr(outsource_task, "order_item_id", None))
        status = getattr(outsource_task, "status", None)
        if (
            item_id not in normalized_item_ids
            or status not in OUTSOURCE_BLOCKING_STATUSES
            or getattr(outsource_task, "deleted_at", None) is not None
        ):
            continue

        summary = blocked.setdefault(
            item_id,
            {
                "outsource_blocked": True,
                "outsource_status": status,
                "outsource_status_label": OUTSOURCE_BLOCKING_STATUS_LABELS[status],
                "outsource_task_count": 0,
                "outsource_task_nos": [],
            },
        )
        summary["outsource_task_count"] += 1
        task_no = getattr(outsource_task, "task_no", None)
        if task_no and task_no not in summary["outsource_task_nos"]:
            summary["outsource_task_nos"].append(str(task_no))
        if status_priority[status] > status_priority[summary["outsource_status"]]:
            summary["outsource_status"] = status
            summary["outsource_status_label"] = OUTSOURCE_BLOCKING_STATUS_LABELS[status]

    return blocked


def _task_type_for_model(model) -> str:
    task_type = {
        "DesignTask": "design",
        "ProductionTask": "production",
        "InstallationTask": "installation",
    }.get(getattr(model, "__name__", ""))
    if not task_type:
        raise ValueError("无法识别任务类型")
    return task_type


async def _validate_order_item_ids(
    db: AsyncSession,
    document_id: UUID,
    raw_item_ids,
    *,
    task_type: str | None = None,
    task_id: UUID | None = None,
    legacy_item_id: UUID | None = None,
) -> list[UUID]:
    """Validate a multi-value item link without guessing historical ownership."""
    if raw_item_ids is None:
        return []
    if not isinstance(raw_item_ids, (list, tuple)):
        raise ValueError("订单明细编号必须是列表")

    item_ids: list[UUID] = []
    seen: set[UUID] = set()
    for raw_item_id in raw_item_ids:
        item_id = _coerce_uuid(raw_item_id)
        if item_id is None:
            raise ValueError("订单明细编号格式不正确")
        if item_id in seen:
            raise ValueError("订单明细不能重复")
        seen.add(item_id)
        item_ids.append(item_id)

    for item_id in item_ids:
        item = await db.get(BusinessDocumentItem, item_id)
        if not item or item.document_id != document_id:
            raise ValueError("订单明细不存在或不属于当前订单")
        if getattr(item, "lifecycle_status", "active") != "active":
            raise ValueError("已作废的订单明细不能关联新任务")

    linked_ids: set[UUID] = set()
    if task_type and task_id:
        linked_ids = set(await _linked_order_item_ids(db, task_type, task_id))
        # Before the many-link table existed, the task model's legacy
        # order_item_id was the only relation. Treat it as already linked so
        # its current work unit can still be progressed after migration.
        if legacy_item_id is not None:
            linked_ids.add(legacy_item_id)

    unlinked_item_ids = [item_id for item_id in item_ids if item_id not in linked_ids]
    if task_type and unlinked_item_ids:
        options = await _task_order_item_option_map(
            db,
            document_id,
            task_type,
            task_id=task_id,
        )
        for item_id in unlinked_item_ids:
            option = options.get(item_id)
            if option is None:
                raise ValueError("订单明细当前进度无法确认，暂不可关联")
            if not option["can_select"]:
                raise ValueError(
                    option["disabled_reason"]
                    or f"订单明细当前处于{option['stage_label']}，不能关联此任务"
                )
    return item_ids


async def _validate_order_item_id(
    db: AsyncSession,
    document_id: UUID,
    raw_item_id,
    *,
    task_type: str | None = None,
    task_id: UUID | None = None,
    legacy_item_id: UUID | None = None,
) -> UUID | None:
    """Validate an optional item link without guessing historical ownership."""
    if raw_item_id in (None, ""):
        return None
    item_ids = await _validate_order_item_ids(
        db,
        document_id,
        [raw_item_id],
        task_type=task_type,
        task_id=task_id,
        legacy_item_id=legacy_item_id,
    )
    return item_ids[0] if item_ids else None


async def _linked_order_item_ids(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
) -> list[UUID]:
    result = await db.execute(
        select(TaskOrderItemLink.order_item_id)
        .where(
            TaskOrderItemLink.task_type == task_type,
            TaskOrderItemLink.task_id == task_id,
        )
        .order_by(TaskOrderItemLink.position, TaskOrderItemLink.order_item_id)
    )
    try:
        scalars = result.scalars()
        if inspect.isawaitable(scalars):
            scalars = await scalars
        values = scalars.all()
        if inspect.isawaitable(values):
            values = await values
    except AttributeError:
        values = []
    return [item_id for value in values if (item_id := _coerce_uuid(value))]


async def _task_order_item_ids(db: AsyncSession, task_type: str, task) -> list[UUID]:
    """Return all linked items, with the legacy column kept as a fallback."""
    ids = await _linked_order_item_ids(db, task_type, task.id)
    legacy_id = _task_order_item_id(task)
    if legacy_id is not None and legacy_id not in ids:
        ids.insert(0, legacy_id)
    return ids


async def _task_order_item_link_rows(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
) -> list[TaskOrderItemLink]:
    result = await db.execute(
        select(TaskOrderItemLink).where(
            TaskOrderItemLink.task_type == task_type,
            TaskOrderItemLink.task_id == task_id,
        ).order_by(TaskOrderItemLink.position, TaskOrderItemLink.order_item_id)
    )
    try:
        scalars = result.scalars()
        if inspect.isawaitable(scalars):
            scalars = await scalars
        rows = scalars.all()
        if inspect.isawaitable(rows):
            rows = await rows
    except AttributeError:
        rows = []
    return [row for row in rows if isinstance(row, TaskOrderItemLink)]


async def _task_link_assignee_names(
    db: AsyncSession,
    links: list[TaskOrderItemLink],
) -> dict[UUID, str]:
    """Resolve only the current per-item executors used by task views."""
    assignee_ids = {
        assignee_id
        for link in links
        if (assignee_id := _coerce_uuid(getattr(link, "assignee_user_id", None)))
    }
    if not assignee_ids:
        return {}
    result = await db.execute(
        select(User.id, User.real_name).where(User.id.in_(assignee_ids))
    )
    try:
        rows = result.all()
        if inspect.isawaitable(rows):
            rows = await rows
    except AttributeError:
        rows = []
    return {
        user_id: real_name
        for row in rows
        for user_id, real_name in [(_coerce_uuid(row[0]), row[1])]
        if user_id is not None and real_name
    }


def _task_item_assignee_state(
    task_type: str,
    status: str | None,
    assignee_user_id: UUID | None,
) -> str:
    """Describe whether a link can still be claimed or is historical."""
    if _is_terminal_item_status(task_type, status or ""):
        return "terminal" if assignee_user_id else "historical_unknown"
    return "claimed" if assignee_user_id else "unassigned"


def _task_item_owner_conflict_message(
    item_ids: list[UUID],
    names_by_item: dict[UUID, str],
) -> str:
    labels = [names_by_item.get(item_id, str(item_id)) for item_id in item_ids]
    return f"所选明细中有明细已由其他员工负责：{'、'.join(labels)}，请取消勾选后再操作"


def _ensure_task_stage_change_permission(
    task_type: str,
    viewer: User | None,
) -> None:
    """Enforce the stage write boundary again inside the service layer."""
    if viewer is not None and not user_has_permission(
        viewer,
        TASK_CHANGE_PERMISSION_BY_TYPE[task_type],
    ):
        raise ValueError(
            f"当前账号只能查看{TASK_TYPE_LABELS[task_type]}流程，不能变更状态"
        )


async def _validate_and_claim_task_items(
    db: AsyncSession,
    task_type: str,
    task,
    selected_ids: list[UUID],
    *,
    viewer: User | None,
    assignee_user_id: UUID | None,
) -> list[TaskOrderItemLink]:
    """Validate ownership for a batch, then claim only selected unassigned links."""
    if viewer is None and assignee_user_id is None:
        # Legacy service-unit callers do not have an authenticated employee
        # context. Real API requests always pass both values, while this path
        # keeps old transition tests and compatibility jobs read-only here.
        return []
    links = await _task_order_item_link_rows(db, task_type, task.id)
    link_by_item = {
        item_id: link
        for link in links
        if (item_id := _coerce_uuid(getattr(link, "order_item_id", None)))
    }
    selected_links = [link_by_item[item_id] for item_id in selected_ids if item_id in link_by_item]
    is_manager = can_assign_task(task_type, viewer)
    conflicts: list[UUID] = []
    for item_id in selected_ids:
        link = link_by_item.get(item_id)
        if link is None:
            continue
        owner_id = _coerce_uuid(getattr(link, "assignee_user_id", None))
        if owner_id and owner_id != assignee_user_id and not is_manager:
            conflicts.append(item_id)
    if conflicts:
        item_names: dict[UUID, str] = {}
        result = await db.execute(
            select(BusinessDocumentItem.id, BusinessDocumentItem.item_name).where(
                BusinessDocumentItem.id.in_(conflicts)
            )
        )
        try:
            rows = result.all()
            if inspect.isawaitable(rows):
                rows = await rows
        except AttributeError:
            rows = []
        item_names = {
            item_id: name
            for row in rows
            for item_id, name in [(_coerce_uuid(row[0]), row[1])]
            if item_id is not None and name
        }
        raise ValueError(_task_item_owner_conflict_message(conflicts, item_names))

    if assignee_user_id is not None:
        for link in selected_links:
            if getattr(link, "assignee_user_id", None) is None:
                link.assignee_user_id = assignee_user_id
    return selected_links


async def _reassign_task_item_links(
    db: AsyncSession,
    task_type: str,
    task,
    raw_item_ids: list[str],
    raw_assignee_user_id,
    *,
    viewer: User | None,
) -> list[UUID]:
    """Reassign only the explicitly named, non-terminal task item links."""
    if not can_assign_task(task_type, viewer):
        raise ValueError(f"当前账号没有{TASK_TYPE_LABELS[task_type]}明细改派权限")

    item_ids: list[UUID] = []
    seen: set[UUID] = set()
    for raw_item_id in raw_item_ids:
        item_id = _coerce_uuid(raw_item_id)
        if item_id is None:
            raise ValueError("订单明细编号格式不正确")
        if item_id in seen:
            raise ValueError("订单明细不能重复")
        seen.add(item_id)
        item_ids.append(item_id)

    links = await _task_order_item_link_rows(db, task_type, task.id)
    links_by_item = {
        item_id: link
        for link in links
        if (item_id := _coerce_uuid(getattr(link, "order_item_id", None)))
    }
    missing = [item_id for item_id in item_ids if item_id not in links_by_item]
    if missing:
        raise ValueError("只能改派已经关联到当前任务的订单明细")
    terminal = [
        item_id
        for item_id in item_ids
        if _is_terminal_item_status(
            task_type,
            getattr(links_by_item[item_id], "item_status", None)
            or getattr(task, "status", "pending"),
        )
    ]
    if terminal:
        raise ValueError("已完成或已取消的订单明细不能重新分配")

    assignee_user_id = await validate_task_assignee(db, raw_assignee_user_id)
    for item_id in item_ids:
        links_by_item[item_id].assignee_user_id = assignee_user_id
    return item_ids


def _is_terminal_task_status(task_type: str, task) -> bool:
    return getattr(task, "status", None) in TASK_TERMINAL_STATUSES.get(task_type, set())


def _select_reusable_stage_task(
    tasks: list,
    task_type: str,
) -> tuple[object | None, bool]:
    """Select the automatic stage card to extend and whether it is reopening.

    Automatic stage progression is order-scoped: a later order item entering
    the same stage must extend the existing card instead of creating a second
    card just because the first batch already finished.  A task with a legacy
    ``order_item_id`` belongs to the manually scoped compatibility path, so a
    terminal task is reusable here only when its scope is carried by the
    multi-item link table (``order_item_id`` is NULL).
    """
    open_task = next(
        (
            candidate
            for candidate in tasks
            if not _is_terminal_task_status(task_type, candidate)
        ),
        None,
    )
    if open_task is not None:
        return open_task, False

    terminal_automatic_task = next(
        (
            candidate
            for candidate in tasks
            if _task_order_item_id(candidate) is None
            and _is_terminal_task_status(task_type, candidate)
        ),
        None,
    )
    return terminal_automatic_task, terminal_automatic_task is not None


async def _ensure_terminal_unlinked_task_is_read_only(
    db: AsyncSession,
    task_type: str,
    task,
) -> None:
    """Block status changes for historical tasks without an item scope."""
    if not _is_terminal_task_status(task_type, task):
        return
    if _task_order_item_id(task) is not None:
        return
    if await _linked_order_item_ids(db, task_type, task.id):
        return
    raise ValueError("历史任务未关联订单明细，已结束任务仅可查看，不能变更状态")


def _new_task_item_state(task_type: str, task) -> tuple[str, int]:
    """Choose a safe initial state for a newly added work unit."""
    status = getattr(task, "status", "pending")
    if _is_terminal_task_status(task_type, task):
        status = {
            "design": "designing",
            "production": "in_progress",
            "installation": "in_progress",
        }[task_type]
    return status, _item_status_progress(
        task_type,
        status,
        int(getattr(task, "progress_pct", 0) or 0),
    )


def _new_unstarted_item_state(task_type: str, task) -> tuple[str, int]:
    """Return the initial state for an item newly added to an open task.

    A task card can already be in progress because another order item is being
    processed. A newly arrived item must still start at the beginning of the
    stage; inheriting the aggregate task state would make it look partially or
    fully completed before anyone handled it.
    """
    if _is_terminal_task_status(task_type, task):
        return _new_task_item_state(task_type, task)
    return "pending", 0


async def _legacy_task_scope_item_ids(
    db: AsyncSession,
    task_type: str,
    task,
) -> list[UUID]:
    """Find current-stage items covered by a legacy whole-order task.

    A task with neither the legacy single-item column nor link rows predates
    item-scoped task processing. Its scope was the order, so narrowing it to
    the first checked item would make a partial completion look complete.
    """
    if _task_order_item_id(task) is not None:
        return []
    if await _linked_order_item_ids(db, task_type, task.id):
        return []

    options = await _task_order_item_option_map(
        db,
        task.document_id,
        task_type,
        task_id=task.id,
    )
    expected_stage = TASK_TYPE_STAGES[task_type]
    return [
        item_id
        for item_id, option in options.items()
        if option.get("stage") == expected_stage and option.get("can_select")
    ]


async def _materialize_legacy_task_scope(
    db: AsyncSession,
    task_type: str,
    task,
) -> list[UUID]:
    """Materialize a legacy order-wide task before a partial status change."""
    item_ids = await _legacy_task_scope_item_ids(db, task_type, task)
    if not item_ids:
        return []

    status, progress = _new_task_item_state(task_type, task)
    await db.execute(
        insert(TaskOrderItemLink.__table__),
        [
            {
                "task_type": task_type,
                "task_id": task.id,
                "order_item_id": item_id,
                "position": position,
                "item_status": status,
                "item_progress_pct": progress,
                "item_completed_at": None,
            }
            for position, item_id in enumerate(item_ids)
        ],
    )
    await db.flush()
    return item_ids


async def _task_item_state_map(
    db: AsyncSession,
    task_type: str,
    task,
) -> dict[UUID, tuple[str, int]]:
    """Return the effective status/progress for every item in one task."""
    fallback_status = getattr(task, "status", "pending")
    fallback_progress = int(getattr(task, "progress_pct", 0) or 0)
    states: dict[UUID, tuple[str, int]] = {
        item_id: (
            fallback_status,
            _item_status_progress(task_type, fallback_status, fallback_progress),
        )
        for item_id in await _task_order_item_ids(db, task_type, task)
    }
    for link in await _task_order_item_link_rows(db, task_type, task.id):
        item_id = _coerce_uuid(link.order_item_id)
        if item_id is None:
            continue
        status = link.item_status or fallback_status
        progress = (
            int(link.item_progress_pct)
            if link.item_progress_pct is not None
            else _item_status_progress(task_type, status, fallback_progress)
        )
        states[item_id] = (status, max(0, min(100, progress)))
    return states


def _aggregate_task_status(task_type: str, statuses: list[str]) -> str:
    """Summarise mixed item states without hiding unfinished work."""
    if not statuses:
        return "pending"
    completed = TASK_COMPLETED_STATUSES.get(task_type, set())
    terminal = TASK_TERMINAL_STATUSES.get(task_type, set())
    if all(status in completed for status in statuses):
        return "confirmed" if task_type == "design" else "completed"
    if all(status in terminal for status in statuses):
        return "cancelled"

    priorities = {
        "design": {"pending": 0, "revision": 1, "designing": 2, "pending_review": 3},
        "production": {"pending": 0, "rework": 1, "in_progress": 2},
        "installation": {"pending": 0, "assigned": 1, "in_progress": 2, "pending_acceptance": 3},
    }
    unfinished = [status for status in statuses if status not in terminal]
    priority = priorities.get(task_type, {})
    return max(unfinished, key=lambda status: priority.get(status, 0))


async def _ensure_task_order_item_links(
    db: AsyncSession,
    task_type: str,
    task,
    item_ids: list[UUID],
) -> None:
    """Add selected item links without unlinking existing work units."""
    existing_ids = set(await _linked_order_item_ids(db, task_type, task.id))
    new_ids = [item_id for item_id in item_ids if item_id not in existing_ids]
    if not new_ids:
        return
    status, progress = _new_unstarted_item_state(task_type, task)
    await db.execute(
        insert(TaskOrderItemLink.__table__),
        [
            {
                "task_type": task_type,
                "task_id": task.id,
                "order_item_id": item_id,
                "position": len(existing_ids) + position,
                "item_status": status,
                "item_progress_pct": progress,
                "item_completed_at": _utc_now() if _is_completed_item_status(task_type, status) else None,
            }
            for position, item_id in enumerate(new_ids)
        ],
    )
    await db.flush()


async def _prepare_status_item_ids(
    db: AsyncSession,
    task_type: str,
    task,
    raw_item_ids: list[str] | None,
) -> list[UUID]:
    """Validate checked items and ensure newly checked items become task links."""
    item_ids = raw_item_ids or []
    if not item_ids:
        legacy_id = _task_order_item_id(task)
        if legacy_id is not None:
            item_ids = [str(legacy_id)]
        else:
            raise ValueError("请先勾选要处理的订单明细")

    legacy_id = _task_order_item_id(task)
    if (
        legacy_id is None
        and not await _linked_order_item_ids(db, task_type, task.id)
    ):
        await _materialize_legacy_task_scope(db, task_type, task)

    validated = await _validate_order_item_ids(
        db,
        task.document_id,
        item_ids,
        task_type=task_type,
        task_id=task.id,
        legacy_item_id=legacy_id,
    )
    await _ensure_task_order_item_links(db, task_type, task, validated)
    return validated


async def _task_item_ids_by_task(
    db: AsyncSession,
    task_type: str,
    tasks: list,
) -> dict[UUID, list[UUID]]:
    task_ids = [task_id for task in tasks if (task_id := _coerce_uuid(getattr(task, "id", None)))]
    linked: dict[UUID, list[UUID]] = {
        task_id: [] for task_id in task_ids
    }
    if task_ids:
        result = await db.execute(
            select(TaskOrderItemLink.task_id, TaskOrderItemLink.order_item_id)
            .where(
                TaskOrderItemLink.task_type == task_type,
                TaskOrderItemLink.task_id.in_(task_ids),
            )
            .order_by(TaskOrderItemLink.position, TaskOrderItemLink.order_item_id)
        )
        try:
            rows = result.all()
            if inspect.isawaitable(rows):
                rows = await rows
        except AttributeError:
            rows = []
        for row in rows:
            try:
                task_id, item_id = row
            except (TypeError, ValueError):
                continue
            task_id = _coerce_uuid(task_id)
            item_id = _coerce_uuid(item_id)
            if task_id is not None and item_id is not None:
                linked.setdefault(task_id, [])
                if item_id not in linked[task_id]:
                    linked[task_id].append(item_id)

    for task in tasks:
        task_id = _coerce_uuid(getattr(task, "id", None))
        if task_id is None:
            continue
        legacy_id = _task_order_item_id(task)
        if legacy_id is not None and legacy_id not in linked.setdefault(task_id, []):
            linked[task_id].insert(0, legacy_id)
    return linked


def _resolve_order_item_stage(
    order_status: str | None,
    item_states: dict[str, list[str]],
    global_states: dict[str, list[str]] | None = None,
) -> str:
    """Resolve one order item's delivery stage from its task history.

    The resolver deliberately treats unknown task statuses as ``not_ready``.
    It may use the order stage as a fallback only when the item has no
    contradictory active task state; this keeps legacy order-level tasks
    usable without guessing an item-level completion that is not present.
    """
    merged_states = {
        stage: list(item_states.get(stage, []))
        for stage in TASK_TYPE_STAGES.values()
    }
    for stage, statuses in (global_states or {}).items():
        merged_states.setdefault(stage, []).extend(statuses)

    recognised_statuses = {
        "designing": DESIGN_IN_PROGRESS_STATUSES
        | DESIGN_COMPLETED_STATUSES
        | {TASK_CANCELLED_STATUS},
        "in_production": PRODUCTION_IN_PROGRESS_STATUSES
        | PRODUCTION_COMPLETED_STATUSES
        | {TASK_CANCELLED_STATUS},
        "in_installation": INSTALLATION_IN_PROGRESS_STATUSES
        | INSTALLATION_COMPLETED_STATUSES
        | {TASK_CANCELLED_STATUS},
    }
    for stage, statuses in merged_states.items():
        if any(status not in recognised_statuses.get(stage, set()) for status in statuses):
            return "not_ready"

    order_status = order_status or ""
    later_than_design = {"in_production", "in_installation", "completed"}
    later_than_production = {"in_installation", "completed"}

    design_statuses = merged_states["designing"]
    if any(status in DESIGN_IN_PROGRESS_STATUSES for status in design_statuses):
        return "designing"
    design_complete = any(
        status in DESIGN_COMPLETED_STATUSES for status in design_statuses
    ) or order_status in later_than_design
    if not design_complete:
        if order_status in {"confirmed", "designing"}:
            return "designing"
        return "not_ready"

    production_statuses = merged_states["in_production"]
    if any(status in PRODUCTION_IN_PROGRESS_STATUSES for status in production_statuses):
        return "in_production"
    production_complete = any(
        status in PRODUCTION_COMPLETED_STATUSES for status in production_statuses
    ) or order_status in later_than_production
    if not production_complete:
        if order_status in {"designing", "in_production", "in_installation", "completed"}:
            return "in_production"
        return "not_ready"

    installation_statuses = merged_states["in_installation"]
    if any(status in INSTALLATION_IN_PROGRESS_STATUSES for status in installation_statuses):
        return "in_installation"
    installation_complete = any(
        status in INSTALLATION_COMPLETED_STATUSES for status in installation_statuses
    ) or order_status == "completed"
    if not installation_complete:
        if order_status in {"designing", "in_production", "in_installation", "completed"}:
            return "in_installation"
        return "not_ready"

    return "completed"


async def _task_stage_states_by_item(
    db: AsyncSession,
    document_id: UUID,
) -> tuple[dict[UUID, dict[str, list[str]]], dict[str, list[str]]]:
    """Collect item-scoped and legacy order-scoped task statuses."""
    from app.models.task import DesignTask, InstallationTask, ProductionTask

    task_models = (
        ("design", DesignTask),
        ("production", ProductionTask),
        ("installation", InstallationTask),
    )
    by_item: dict[UUID, dict[str, list[str]]] = {}
    global_states: dict[str, list[str]] = {
        stage: [] for stage in TASK_TYPE_STAGES.values()
    }

    for task_type, model in task_models:
        result = await db.execute(
            select(model).where(model.document_id == document_id)
        )
        tasks = list(result.scalars().all())
        item_ids_by_task = await _task_item_ids_by_task(db, task_type, tasks)
        link_state_by_item: dict[tuple[UUID, UUID], str] = {}
        task_ids = [
            task_id for task in tasks
            if (task_id := _coerce_uuid(getattr(task, "id", None))) is not None
        ]
        if task_ids:
            link_result = await db.execute(
                select(TaskOrderItemLink).where(
                    TaskOrderItemLink.task_type == task_type,
                    TaskOrderItemLink.task_id.in_(task_ids),
                )
            )
            try:
                link_rows = list(link_result.scalars().all())
            except AttributeError:
                link_rows = []
            for link in link_rows:
                task_id = _coerce_uuid(getattr(link, "task_id", None))
                item_id = _coerce_uuid(getattr(link, "order_item_id", None))
                item_status = getattr(link, "item_status", None)
                if task_id and item_id and item_status:
                    link_state_by_item[(task_id, item_id)] = item_status
        stage = TASK_TYPE_STAGES[task_type]
        for task in tasks:
            task_id = _coerce_uuid(getattr(task, "id", None))
            status = getattr(task, "status", None)
            if task_id is None or not isinstance(status, str):
                global_states[stage].append("unknown")
                continue
            linked_ids = item_ids_by_task.get(task_id, [])
            if not linked_ids:
                global_states[stage].append(status)
                continue
            for item_id in linked_ids:
                item_status = link_state_by_item.get((task_id, item_id), status)
                by_item.setdefault(item_id, {}).setdefault(stage, []).append(item_status)

    return by_item, global_states


async def _task_order_item_option_map(
    db: AsyncSession,
    document_id: UUID,
    task_type: str,
    *,
    task_id: UUID | None = None,
    viewer: User | None = None,
) -> dict[UUID, dict]:
    """Build the authoritative order-item option catalog for one task type."""
    if task_type not in TASK_TYPE_STAGES:
        raise ValueError("不支持的任务类型")

    order = await db.get(BusinessDocument, document_id)
    if (
        not order
        or order.doc_type != "order"
        or order.deleted_at is not None
    ):
        raise ValueError("关联订单不存在或已取消")

    item_result = await db.execute(
        select(BusinessDocumentItem)
        .where(
            BusinessDocumentItem.document_id == document_id,
            BusinessDocumentItem.lifecycle_status == "active",
        )
        .order_by(BusinessDocumentItem.sort_order, BusinessDocumentItem.id)
    )
    items = list(item_result.scalars().all())
    states_by_item, global_states = await _task_stage_states_by_item(
        db,
        document_id,
    )
    expected_stage = TASK_TYPE_STAGES[task_type]
    linked_by_item: dict[UUID, TaskOrderItemLink] = {}
    if task_id is not None:
        linked_by_item = {
            item_id: link
            for link in await _task_order_item_link_rows(db, task_type, task_id)
            if (item_id := _coerce_uuid(link.order_item_id)) is not None
        }
    linked_rows = list(linked_by_item.values())
    assignee_names = await _task_link_assignee_names(db, linked_rows)
    can_manage_items = can_assign_task(task_type, viewer)
    can_change_stage = viewer is None or user_has_permission(
        viewer,
        TASK_CHANGE_PERMISSION_BY_TYPE[task_type],
    )
    current_employee_user_id: UUID | None = None
    if viewer is not None and not can_manage_items:
        try:
            current_employee_user_id = await resolve_current_employee_user_id(db, viewer)
        except ValueError:
            # The options API remains readable for an account whose employee
            # binding is incomplete, but its checkboxes become read-only.
            current_employee_user_id = None
    outsource_by_item = await _blocking_outsource_map(
        db,
        document_id,
        task_type,
        [item_id for item in items if (item_id := _coerce_uuid(item.id)) is not None],
    )
    options: dict[UUID, dict] = {}

    for item in items:
        item_id = _coerce_uuid(item.id)
        if item_id is None:
            continue
        stage = _resolve_order_item_stage(
            order.status,
            states_by_item.get(item_id, {}),
            global_states,
        )
        link = linked_by_item.get(item_id)
        is_linked = link is not None
        task_status = link.item_status if link else None
        task_progress_pct = (
            int(link.item_progress_pct)
            if link and link.item_progress_pct is not None
            else None
        )
        assignee_user_id = (
            _coerce_uuid(getattr(link, "assignee_user_id", None))
            if link
            else None
        )
        assignee_name = assignee_names.get(assignee_user_id) if assignee_user_id else None
        assignee_state = _task_item_assignee_state(
            task_type,
            task_status,
            assignee_user_id,
        )
        outsource = outsource_by_item.get(item_id, {
            "outsource_blocked": False,
            "outsource_status": None,
            "outsource_status_label": None,
            "outsource_task_count": 0,
            "outsource_task_nos": [],
        })
        can_view_outsource = can_view_outsource_tasks(viewer)
        if is_linked:
            can_select = can_change_stage and not _is_terminal_item_status(task_type, task_status or "")
            if (
                can_select
                and assignee_user_id is not None
                and not can_manage_items
                and assignee_user_id != current_employee_user_id
            ):
                can_select = False
                disabled_reason = f"该明细由{assignee_name or '其他员工'}负责"
            elif (
                can_select
                and viewer is not None
                and not can_manage_items
                and current_employee_user_id is None
            ):
                can_select = False
                disabled_reason = "当前账号未绑定在职员工，不能领取明细"
            elif not can_change_stage:
                disabled_reason = f"当前账号只能查看{TASK_TYPE_LABELS[task_type]}流程，不能变更状态"
            elif can_select:
                disabled_reason = None
            elif _is_completed_item_status(task_type, task_status or ""):
                disabled_reason = "该明细在本任务中已完成，不能再次处理"
            else:
                disabled_reason = "该明细在本任务中已取消"
        else:
            can_select = can_change_stage and stage == expected_stage and not outsource["outsource_blocked"]
            if (
                can_select
                and viewer is not None
                and not can_manage_items
                and current_employee_user_id is None
            ):
                can_select = False
                disabled_reason = "当前账号未绑定在职员工，不能领取明细"
            elif not can_change_stage:
                disabled_reason = f"当前账号只能查看{TASK_TYPE_LABELS[task_type]}流程，不能变更状态"
            elif outsource["outsource_blocked"] and can_view_outsource:
                disabled_reason = (
                    f"{outsource['outsource_status_label']}，完成后才能关联"
                    f"{TASK_TYPE_LABELS[task_type]}任务"
                )
            elif outsource["outsource_blocked"]:
                disabled_reason = (
                    f"当前明细有未完成的前置事项，完成后才能关联"
                    f"{TASK_TYPE_LABELS[task_type]}任务"
                )
            elif can_select:
                disabled_reason = None
            elif stage == "completed":
                disabled_reason = "该明细已完成，不能再次关联任务"
            elif stage == "not_ready":
                disabled_reason = "当前进度无法确认，暂不可关联"
            else:
                disabled_reason = (
                    f"当前处于{ORDER_ITEM_STAGE_LABELS[stage]}，不能关联"
                    f"{TASK_TYPE_LABELS[task_type]}任务"
                )

        can_view_item_price = viewer is not None and user_has_permission(
            viewer,
            PERM_ORDER_ITEM_VIEW_PRICE,
        )
        item_payload = {}
        for field_name in OrderItemResponse.model_fields:
            value = getattr(item, field_name, None)
            if field_name in ORDER_ITEM_PRICE_FIELDS and not can_view_item_price:
                value = None
            item_payload[field_name] = str(value) if isinstance(value, UUID) else value
        payload = {
            **TaskOrderItemOption.model_validate({
                **item_payload,
                "stage": stage,
                "stage_label": ORDER_ITEM_STAGE_LABELS[stage],
                "stage_view": make_status_view(
                    stage,
                    ORDER_ITEM_STAGE_LABELS[stage],
                    terminal=stage == "completed",
                ).model_dump(mode="json"),
                "can_select": can_select,
                "disabled_reason": disabled_reason,
                "is_linked": is_linked,
                "task_status": task_status,
                "assignee_user_id": str(assignee_user_id) if assignee_user_id else None,
                "assignee_name": assignee_name,
                "assignee_state": assignee_state,
                "task_status_label": _item_status_label(task_type, task_status),
                "task_status_view": (
                    _task_status_view(task_type, task_status).model_dump(mode="json")
                    if task_status
                    else None
                ),
                "task_progress_pct": task_progress_pct,
                "capabilities": {
                    "select": make_action_capability(
                        can_select,
                        disabled_reason,
                    ).model_dump(mode="json"),
                },
                **visible_outsource_fields(viewer, outsource),
            }).model_dump(
                mode="json",
                exclude_none=not can_view_item_price,
            ),
        }
        options[item_id] = payload

    return options


async def get_task_order_item_options(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
    viewer: User | None = None,
) -> list[dict]:
    """Return active order items with current stage and link eligibility."""
    from app.models.task import DesignTask, InstallationTask, ProductionTask

    task_models = {
        "design": DesignTask,
        "production": ProductionTask,
        "installation": InstallationTask,
    }
    model = task_models.get(task_type)
    if model is None:
        raise ValueError("不支持的任务类型")
    task = await get_visible_task(db, model, task_id, viewer)
    if not task:
        raise ValueError("任务不存在或当前账号无权查看")
    options = await _task_order_item_option_map(
        db,
        task.document_id,
        task_type,
        task_id=task_id,
        viewer=viewer,
    )
    return list(options.values())


async def _sync_task_order_item_links(
    db: AsyncSession,
    task_type: str,
    task,
    item_ids: list[UUID],
    *,
    previous_legacy_item_id: UUID | None = None,
    new_item_state: tuple[str, int] | None = None,
    reset_existing: bool = False,
) -> None:
    """Replace one task's links atomically inside the current transaction.

    ``reset_existing`` is reserved for an explicit stage rollback. Normal
    task grouping must preserve the status of already-linked details; a
    rollback intentionally turns those historical details back into work.
    """
    if previous_legacy_item_id is None:
        legacy_scope_ids = await _materialize_legacy_task_scope(
            db,
            task_type,
            task,
        )
        if legacy_scope_ids:
            item_ids = list(dict.fromkeys([*legacy_scope_ids, *item_ids]))

    existing_rows = await _task_order_item_link_rows(db, task_type, task.id)
    existing_by_item = {
        item_id: row
        for row in existing_rows
        if (item_id := _coerce_uuid(row.order_item_id)) is not None
    }
    await db.execute(
        delete(TaskOrderItemLink).where(
            TaskOrderItemLink.task_type == task_type,
            TaskOrderItemLink.task_id == task.id,
        )
    )
    if item_ids:
        new_status, new_progress = (
            new_item_state
            if new_item_state is not None
            else _new_unstarted_item_state(task_type, task)
        )
        link_payload = []
        for position, item_id in enumerate(item_ids):
            existing = existing_by_item.get(item_id)
            if reset_existing and existing is not None:
                item_status = new_status
                item_progress = new_progress
                item_completed_at = None
            else:
                item_status = getattr(existing, "item_status", None) or new_status
                item_progress = getattr(existing, "item_progress_pct", None)
                if item_progress is None:
                    item_progress = new_progress
                item_completed_at = getattr(existing, "item_completed_at", None)
                if item_completed_at is None and _is_completed_item_status(task_type, item_status):
                    item_completed_at = _utc_now()
            link_payload.append(
                {
                    "task_type": task_type,
                    "task_id": task.id,
                    "order_item_id": item_id,
                    "assignee_user_id": _coerce_uuid(
                        getattr(existing, "assignee_user_id", None)
                    ) if existing is not None else None,
                    "position": position,
                    "item_status": item_status,
                    "item_progress_pct": item_progress,
                    "item_completed_at": item_completed_at,
                }
            )
        await db.execute(
            insert(TaskOrderItemLink.__table__),
            link_payload,
        )
    setattr(task, "_linked_order_item_ids", list(item_ids))
    await db.flush()

    states = await _task_item_state_map(db, task_type, task)
    aggregate_status = _aggregate_task_status(
        task_type,
        [status for status, _ in states.values()],
    )
    aggregate_progress = round(
        sum(item_progress for _, item_progress in states.values()) / len(states)
    ) if states else 0
    task.status = aggregate_status
    task.progress_pct = max(0, min(100, aggregate_progress))
    if all(
        _is_completed_item_status(task_type, status)
        for status, _ in states.values()
    ) and states:
        task.completed_at = _utc_now()
    elif aggregate_status != "cancelled":
        task.completed_at = None
    await db.flush()


async def _clear_task_order_item_links(
    db: AsyncSession,
    task_type: str,
    task_ids: list[UUID],
) -> None:
    if not task_ids:
        return
    await db.execute(
        delete(TaskOrderItemLink).where(
            TaskOrderItemLink.task_type == task_type,
            TaskOrderItemLink.task_id.in_(task_ids),
        )
    )


def _attachment_to_dict(att) -> dict:
    return AttachmentResponse.model_validate(att).model_dump(mode="json")


async def _enrich_task_order(
    db,
    task_dict: dict,
    *,
    viewer: User | None = None,
) -> dict:
    """Add operational order context and only expose total with explicit permission."""
    doc_id = task_dict.get("document_id") or task_dict.get("order_id")
    if not doc_id:
        return task_dict
    can_view_order_price = viewer is not None and user_has_permission(
        viewer,
        PERM_ORDER_VIEW_PRICE,
    )
    if not can_view_order_price:
        task_dict.pop("total_amount", None)
    order_columns = "doc_no, customer_name, department, contact_person, contact_phone"
    if can_view_order_price:
        order_columns += ", total_amount"
    row = (await db.execute(
        text(f"SELECT {order_columns} FROM business_documents WHERE id = :id"),
        {"id": doc_id},
    )).fetchone()
    if row:
        task_dict["order_no"] = row[0]
        task_dict["customer_name"] = row[1]
        task_dict["department"] = row[2]
        # Installation tasks can have a task-specific现场联系人; design and
        # production tasks use the order contact as their shared source.
        task_dict["contact_name"] = task_dict.get("contact_name") or row[3]
        task_dict["contact_phone"] = task_dict.get("contact_phone") or row[4]
        if can_view_order_price:
            task_dict["total_amount"] = float(row[5]) if row[5] is not None else None
        task_dict["source"] = "订单"
    # Resolve assigned_to user name
    assigned_to = task_dict.get("assigned_to")
    if assigned_to:
        user_row = (await db.execute(
            text("SELECT real_name FROM users WHERE id = :id"),
            {"id": str(assigned_to)},
        )).fetchone()
        if user_row:
            task_dict["assigned_to_name"] = user_row[0]
    task_type = task_dict.pop("_task_type", None)
    order_item_id = task_dict.get("order_item_id")
    linked_ids: list[UUID] = []
    task_uuid = _coerce_uuid(task_dict.get("id"))
    if task_type and task_uuid is not None:
        linked_ids = await _linked_order_item_ids(
            db,
            task_type,
            task_uuid,
        )
    legacy_id = _coerce_uuid(order_item_id)
    if legacy_id is not None and legacy_id not in linked_ids:
        linked_ids.insert(0, legacy_id)
    if linked_ids:
        item_result = await db.execute(
            select(BusinessDocumentItem.id, BusinessDocumentItem.item_name).where(
                BusinessDocumentItem.id.in_(linked_ids)
            )
        )
        item_rows = item_result.all()
        if inspect.isawaitable(item_rows):
            item_rows = await item_rows
        item_names_by_id = {
            str(row[0]): row[1]
            for row in item_rows
        }
        names = [
            item_names_by_id[str(item_id)]
            for item_id in linked_ids
            if str(item_id) in item_names_by_id
        ]
        task_dict["order_item_ids"] = [str(item_id) for item_id in linked_ids]
        task_dict["item_names"] = names
        task_dict["order_item_id"] = str(linked_ids[0])
        task_dict["item_name"] = "、".join(names) if names else task_dict.get("item_name")
    else:
        task_dict["order_item_ids"] = []
        task_dict["item_names"] = []

    item_states: dict[str, dict] = {}
    if task_type and task_uuid is not None and linked_ids:
        fallback_status = task_dict.get("status", "pending")
        fallback_progress = int(task_dict.get("progress_pct", 0) or 0)
        link_rows = await _task_order_item_link_rows(db, task_type, task_uuid)
        link_by_item = {
            item_id: link
            for link in link_rows
            if (item_id := _coerce_uuid(link.order_item_id)) is not None
        }
        assignee_names = await _task_link_assignee_names(db, link_rows)
        for item_id in linked_ids:
            link = link_by_item.get(item_id)
            status = (link.item_status if link and link.item_status else fallback_status)
            progress = (
                int(link.item_progress_pct)
                if link and link.item_progress_pct is not None
                else _item_status_progress(task_type, status, fallback_progress)
            )
            assignee_user_id = (
                _coerce_uuid(getattr(link, "assignee_user_id", None))
                if link
                else None
            )
            item_states[str(item_id)] = {
                "status": status,
                "status_label": _item_status_label(task_type, status),
                "progress_pct": max(0, min(100, progress)),
                "status_view": _task_status_view(task_type, status).model_dump(mode="json"),
                "capabilities": _task_capabilities(task_type, status),
                "assignee_user_id": str(assignee_user_id) if assignee_user_id else None,
                "assignee_name": assignee_names.get(assignee_user_id) if assignee_user_id else None,
                "assignee_state": _task_item_assignee_state(
                    task_type,
                    status,
                    assignee_user_id,
                ),
            }
    task_dict["order_item_states"] = item_states
    return task_dict


async def _refresh_task_for_response(db: AsyncSession, task) -> None:
    """显式加载异步 ORM 字段，避免响应序列化触发隐式数据库 IO。"""
    await db.refresh(task)
    await db.refresh(task, ["attachments"])


async def _prepare_task_create_data(
    db: AsyncSession,
    data: dict,
    *,
    allowed_order_statuses: tuple[str, ...],
    task_label: str,
    task_type: str | None = None,
) -> tuple[dict, list[UUID]]:
    """校验父订单并把前端兼容字段转换为任务模型字段。"""
    normalized = dict(data)
    raw_order_id = normalized.pop("order_id", None) or normalized.get(
        "document_id"
    )
    if not raw_order_id:
        raise ValueError("请选择关联订单")
    order_id = (
        raw_order_id
        if isinstance(raw_order_id, UUID)
        else UUID(str(raw_order_id))
    )
    order = await db.get(BusinessDocument, order_id)
    if (
        not order
        or order.doc_type != "order"
        or order.deleted_at is not None
    ):
        raise ValueError("关联订单不存在或已取消")
    if order.status not in allowed_order_statuses:
        allowed_text = "、".join(allowed_order_statuses)
        raise ValueError(
            f"订单当前状态不能创建{task_label}任务，允许状态：{allowed_text}"
        )
    if not order.customer_id:
        raise ValueError("订单未关联正式客户，请先完善客户资料")

    normalized["document_id"] = order_id
    has_single_item_id = "order_item_id" in normalized
    has_multiple_item_ids = "order_item_ids" in normalized
    if has_single_item_id and has_multiple_item_ids:
        raise ValueError("不能同时提交订单明细编号和订单明细编号列表")
    if has_multiple_item_ids:
        item_ids = await _validate_order_item_ids(
            db,
            order_id,
            normalized.pop("order_item_ids"),
            task_type=task_type,
        )
        normalized["order_item_id"] = item_ids[0] if item_ids else None
    elif has_single_item_id:
        item_id = await _validate_order_item_id(
            db,
            order_id,
            normalized.get("order_item_id"),
            task_type=task_type,
        )
        item_ids = [item_id] if item_id is not None else []
    else:
        item_ids = []
    if not item_ids:
        raise ValueError(
            f"创建{task_label}任务至少选择一条订单明细，不能创建未关联订单明细任务"
        )
    normalized["customer_id"] = order.customer_id
    normalized["project_name"] = (
        (normalized.get("project_name") or "").strip()
        or order.project_name
    )
    for field in ("assigned_to", "material_id", "process_id"):
        if field not in normalized:
            continue
        value = normalized[field]
        normalized[field] = (
            UUID(str(value))
            if value and not isinstance(value, UUID)
            else value or None
        )
    if normalized.get("scheduled_at") and isinstance(
        normalized["scheduled_at"],
        str,
    ):
        normalized["scheduled_at"] = datetime.fromisoformat(
            normalized["scheduled_at"]
        )
    return normalize_task_schedule_data(normalized), item_ids


async def _attach_outsource_flags(
    db: AsyncSession,
    task_type: str,
    task_dicts: list[dict],
    viewer: User | None = None,
) -> list[dict]:
    """为任务列表批量补 is_outsourced：存在未删除的关联外协任务即 True。"""
    if not can_view_outsource_tasks(viewer):
        for task_dict in task_dicts:
            task_dict["is_outsourced"] = False
        return task_dicts

    from app.models.outsource import OutsourceTask
    ids = [d.get("id") for d in task_dicts if d.get("id")]
    linked: set[str] = set()
    if ids:
        result = await db.execute(
            select(OutsourceTask.source_task_id).where(
                OutsourceTask.source_task_type == task_type,
                OutsourceTask.source_task_id.in_([UUID(i) for i in ids]),
                OutsourceTask.deleted_at.is_(None),
            )
        )
        linked = {str(x) for x in result.scalars().all()}
    for d in task_dicts:
        d["is_outsourced"] = str(d.get("id")) in linked
    return task_dicts


async def _clear_outsource_source_refs(db: AsyncSession, task_type: str, task_ids: list[UUID]) -> None:
    """删除任务后清空外协任务对来源任务的悬空引用（source_task_id 无外键）。"""
    if not task_ids:
        return
    from sqlalchemy import update as sa_update

    from app.models.outsource import OutsourceTask
    await db.execute(
        sa_update(OutsourceTask)
        .where(
            OutsourceTask.source_task_type == task_type,
            OutsourceTask.source_task_id.in_(task_ids),
        )
        .values(source_task_type=None, source_task_id=None)
    )


async def _all_stage_tasks_completed(
    db: AsyncSession,
    doc_id: UUID,
    model,
    terminal_statuses: set[str],
) -> bool:
    """Check every active order item and preserve legacy order-level tasks."""
    item_result = await db.execute(
        select(BusinessDocumentItem).where(
            BusinessDocumentItem.document_id == doc_id,
            BusinessDocumentItem.lifecycle_status == "active",
        )
    )
    active_items = list(item_result.scalars().all())
    task_result = await db.execute(select(model).where(model.document_id == doc_id))
    tasks = list(task_result.scalars().all())
    task_type = _task_type_for_model(model)
    item_ids_by_task = await _task_item_ids_by_task(db, task_type, tasks)
    link_statuses: dict[tuple[UUID, UUID], str] = {}
    task_ids = [
        task_id for task in tasks
        if (task_id := _coerce_uuid(getattr(task, "id", None))) is not None
    ]
    if task_ids:
        link_result = await db.execute(
            select(TaskOrderItemLink).where(
                TaskOrderItemLink.task_type == task_type,
                TaskOrderItemLink.task_id.in_(task_ids),
            )
        )
        try:
            for link in link_result.scalars().all():
                task_id = _coerce_uuid(getattr(link, "task_id", None))
                item_id = _coerce_uuid(getattr(link, "order_item_id", None))
                item_status = getattr(link, "item_status", None)
                if task_id and item_id and item_status:
                    link_statuses[(task_id, item_id)] = item_status
        except AttributeError:
            pass

    def linked_items(task) -> list[UUID]:
        task_id = _coerce_uuid(getattr(task, "id", None))
        return item_ids_by_task.get(task_id, []) if task_id is not None else []

    if active_items:
        active_ids = {item.id for item in active_items}
        relevant_tasks = [
            task for task in tasks
            if not linked_items(task)
            or any(item_id in active_ids for item_id in linked_items(task))
        ]
        for item_id in active_ids:
            item_tasks = [
                task for task in relevant_tasks
                if item_id in linked_items(task)
            ]
            if not item_tasks or any(
                link_statuses.get(
                    (_coerce_uuid(task.id), item_id),
                    task.status,
                ) not in terminal_statuses
                for task in item_tasks
            ):
                return False
        if any(
            task.status not in terminal_statuses
            for task in relevant_tasks
            if not linked_items(task)
        ):
            return False
        return bool(relevant_tasks)

    return bool(tasks) and all(
        task.status in terminal_statuses for task in tasks
    )


async def _item_stage_tasks_completed(
    db: AsyncSession,
    doc_id: UUID,
    item_id: UUID,
    model,
    terminal_statuses: set[str],
) -> bool:
    result = await db.execute(select(model).where(model.document_id == doc_id))
    tasks = list(result.scalars().all())
    item_ids_by_task = await _task_item_ids_by_task(
        db,
        _task_type_for_model(model),
        tasks,
    )
    tasks = [
        task for task in tasks
        if item_id in item_ids_by_task.get(_coerce_uuid(task.id), [])
    ]
    link_statuses: dict[tuple[UUID, UUID], str] = {}
    task_ids = [
        task_id for task in tasks
        if (task_id := _coerce_uuid(getattr(task, "id", None))) is not None
    ]
    if task_ids:
        link_result = await db.execute(
            select(TaskOrderItemLink).where(
                TaskOrderItemLink.task_type == _task_type_for_model(model),
                TaskOrderItemLink.task_id.in_(task_ids),
            )
        )
        try:
            for link in link_result.scalars().all():
                task_id = _coerce_uuid(getattr(link, "task_id", None))
                linked_item_id = _coerce_uuid(getattr(link, "order_item_id", None))
                item_status = getattr(link, "item_status", None)
                if task_id and linked_item_id and item_status:
                    link_statuses[(task_id, linked_item_id)] = item_status
        except AttributeError:
            pass
    return bool(tasks) and all(
        link_statuses.get((_coerce_uuid(task.id), item_id), task.status)
        in terminal_statuses
        for task in tasks
    )


async def _create_production_task_for_item(
    db: AsyncSession,
    task,
    item_id: UUID | None = None,
) -> None:
    """Add an item to the order's active production task card.

    Automatic stage progression used to create one production row per item.
    Reuse the first open card instead and let the link table carry the
    independent item state.
    """
    item_ids = (
        [item_id]
        if item_id is not None
        else await _task_order_item_ids(db, "design", task)
    )
    if not item_ids:
        return
    from app.models.task import ProductionTask

    order = await db.get(BusinessDocument, task.document_id)
    if not order:
        return
    for current_item_id in item_ids:
        if current_item_id is None:
            continue
        item = await db.get(BusinessDocumentItem, current_item_id)
        if not item:
            continue
        existing_result = await db.execute(
            select(ProductionTask)
            .where(
                ProductionTask.document_id == task.document_id,
                ProductionTask.status != "cancelled",
            )
            .order_by(ProductionTask.created_at.asc(), ProductionTask.id.asc())
        )
        existing_tasks = list(existing_result.scalars().all())
        existing_item_ids = await _task_item_ids_by_task(
            db,
            "production",
            existing_tasks,
        )
        if any(
            current_item_id in linked_ids
            for linked_ids in existing_item_ids.values()
        ):
            continue

        target, reused_terminal_task = _select_reusable_stage_task(
            existing_tasks,
            "production",
        )
        if target is None:
            target = ProductionTask(
                production_no=await generate_production_no(db),
                document_id=task.document_id,
                order_item_id=None,
                customer_id=order.customer_id,
                project_name=order.project_name,
                status="pending",
                material_id=item.material_id,
                process_id=item.process_id,
                length=item.length,
                width=item.width,
                height=item.height,
                quantity=item.quantity,
            )
            db.add(target)
            await db.flush()

        target_item_ids = await _task_order_item_ids(db, "production", target)
        sync_kwargs = (
            {"new_item_state": ("pending", 0)}
            if reused_terminal_task
            else {}
        )
        await _sync_task_order_item_links(
            db,
            "production",
            target,
            list(dict.fromkeys([*target_item_ids, current_item_id])),
            **sync_kwargs,
        )


async def _create_installation_task_for_item(
    db: AsyncSession,
    task,
    item_id: UUID | None = None,
) -> None:
    """Add an item to the order's active installation task card."""
    item_ids = (
        [item_id]
        if item_id is not None
        else await _task_order_item_ids(db, "production", task)
    )
    if not item_ids:
        return
    from app.models.task import InstallationTask

    order = await db.get(BusinessDocument, task.document_id)
    if not order:
        return
    for current_item_id in item_ids:
        if current_item_id is None:
            continue
        item = await db.get(BusinessDocumentItem, current_item_id)
        if not item:
            continue
        existing_result = await db.execute(
            select(InstallationTask)
            .where(
                InstallationTask.document_id == task.document_id,
                InstallationTask.status != "cancelled",
            )
            .order_by(InstallationTask.created_at.asc(), InstallationTask.id.asc())
        )
        existing_tasks = list(existing_result.scalars().all())
        existing_item_ids = await _task_item_ids_by_task(
            db,
            "installation",
            existing_tasks,
        )
        if any(
            current_item_id in linked_ids
            for linked_ids in existing_item_ids.values()
        ):
            continue

        target, reused_terminal_task = _select_reusable_stage_task(
            existing_tasks,
            "installation",
        )
        if target is None:
            target = InstallationTask(
                installation_no=await generate_installation_no(db),
                document_id=task.document_id,
                order_item_id=None,
                customer_id=order.customer_id,
                project_name=order.project_name,
                status="pending",
                address=order.installation_address,
                contact_name=order.contact_person,
                contact_phone=order.contact_phone,
            )
            db.add(target)
            await db.flush()

        target_item_ids = await _task_order_item_ids(db, "installation", target)
        sync_kwargs = (
            {"new_item_state": ("pending", 0)}
            if reused_terminal_task
            else {}
        )
        await _sync_task_order_item_links(
            db,
            "installation",
            target,
            list(dict.fromkeys([*target_item_ids, current_item_id])),
            **sync_kwargs,
        )


async def _maybe_advance_order_stage(
    db: AsyncSession,
    doc_id: UUID,
    from_status: str,
    to_status: str,
    model,
    terminal_statuses: set[str],
    reason: str,
    operated_by: UUID | None,
) -> None:
    order = await db.get(BusinessDocument, doc_id)
    if not order or order.status != from_status:
        return
    if not await _all_stage_tasks_completed(db, doc_id, model, terminal_statuses):
        return
    order.status = to_status
    from app.services.business_document_service import BusinessDocumentService

    order_svc = BusinessDocumentService(db, doc_type="order")
    await order_svc.repo.create_status_log(
        doc_id, from_status, to_status, reason, operated_by
    )
    await db.flush()


async def _all_execution_tasks_completed(db: AsyncSession, doc_id: UUID) -> bool:
    """Return whether every active item and legacy task is terminal."""
    from app.models.task import DesignTask, InstallationTask, ProductionTask

    task_rules = (
        (DesignTask, {"confirmed", "completed", "cancelled"}),
        (ProductionTask, {"completed", "cancelled"}),
        (InstallationTask, {"completed", "cancelled"}),
    )
    for model, terminal_statuses in task_rules:
        if not await _all_stage_tasks_completed(
            db, doc_id, model, terminal_statuses
        ):
            return False
    return True


async def _maybe_complete_order(db: AsyncSession, doc_id: UUID, operated_by: UUID | None) -> None:
    """Complete an installation-stage order only after all task types finish."""
    order = await db.get(BusinessDocument, doc_id)
    if not order or order.status != "in_installation":
        return
    if not await _all_execution_tasks_completed(db, doc_id):
        return

    from app.services.business_document_service import BusinessDocumentService

    order_svc = BusinessDocumentService(db, doc_type="order")
    try:
        await order_svc.change_status(
            doc_id,
            "completed",
            "所有设计、制作、安装任务已完成，系统自动推进",
            operated_by,
        )
    except ValueError:
        # Keep the task update successful if an unrelated order guard blocks
        # aggregate completion. The order can still be advanced manually.
        return


async def _apply_task_item_status_change(
    db: AsyncSession,
    task_type: str,
    task,
    to_status: str,
    raw_item_ids: list[str] | None,
    viewer: User | None = None,
    assignee_user_id: UUID | None = None,
    operated_by: UUID | None = None,
) -> tuple[list[UUID], dict[UUID, tuple[str, int]]]:
    """Apply one status transition only to the checked item work units."""
    _ensure_task_stage_change_permission(task_type, viewer)
    workflows = {
        "design": DESIGN_TASK_WORKFLOW,
        "production": PRODUCTION_TASK_WORKFLOW,
        "installation": INSTALLATION_TASK_WORKFLOW,
    }
    workflow = workflows[task_type]
    selected_ids = await _prepare_status_item_ids(
        db,
        task_type,
        task,
        raw_item_ids,
    )
    states = await _task_item_state_map(db, task_type, task)
    previous_statuses: dict[UUID, str] = {}
    for item_id in selected_ids:
        current_status = states.get(item_id, (getattr(task, "status", "pending"), 0))[0]
        previous_statuses[item_id] = current_status
        if to_status not in allowed_targets(workflow, current_status):
            current_label = _item_status_label(task_type, current_status) or "当前状态"
            target_label = _item_status_label(task_type, to_status) or "目标状态"
            next_statuses = [
                status
                for status in allowed_targets(workflow, current_status)
                if status != TASK_CANCELLED_STATUS
            ]
            if next_statuses:
                next_label = _item_status_label(task_type, next_statuses[0]) or "下一步状态"
                raise ValueError(
                    f"所选订单明细当前为“{current_label}”，不能直接标记为“{target_label}”，"
                    f"请先推进到“{next_label}”。"
                )
            raise ValueError(
                f"所选订单明细当前为“{current_label}”，不能变更为“{target_label}”。"
            )

    if task_type in OUTSOURCE_BLOCKING_TASK_TYPES and _is_completed_item_status(task_type, to_status):
        blocked_outsource = await _blocking_outsource_map(
            db,
            task.document_id,
            task_type,
            selected_ids,
        )
        if blocked_outsource:
            task_nos = [
                task_no
                for summary in blocked_outsource.values()
                for task_no in summary["outsource_task_nos"]
            ]
            if can_view_outsource_tasks(viewer):
                task_ref = f"（外协任务：{'、'.join(task_nos)}）" if task_nos else ""
                raise ValueError(
                    f"所选订单明细存在未完成的外协任务{task_ref}，"
                    f"外协完成后才能完成{TASK_TYPE_LABELS[task_type]}任务"
                )
            raise ValueError(
                f"所选订单明细存在未完成的前置事项，完成后才能完成"
                f"{TASK_TYPE_LABELS[task_type]}任务"
            )

    selected_links = await _validate_and_claim_task_items(
        db,
        task_type,
        task,
        selected_ids,
        viewer=viewer,
        assignee_user_id=assignee_user_id,
    )
    event_assignees = {
        _coerce_uuid(link.order_item_id): (
            _coerce_uuid(getattr(link, "assignee_user_id", None))
            or assignee_user_id
        )
        for link in selected_links
        if _coerce_uuid(link.order_item_id) is not None
    }
    if to_status in TASK_RELEASE_STATUSES.get(task_type, set()):
        for link in selected_links:
            link.assignee_user_id = None

    progress = _item_status_progress(
        task_type,
        to_status,
        int(getattr(task, "progress_pct", 0) or 0),
    )
    await db.execute(
        update(TaskOrderItemLink)
        .where(
            TaskOrderItemLink.task_type == task_type,
            TaskOrderItemLink.task_id == task.id,
            TaskOrderItemLink.order_item_id.in_(selected_ids),
        )
        .values(
            item_status=to_status,
            item_progress_pct=progress,
            item_completed_at=(
                _utc_now() if _is_completed_item_status(task_type, to_status) else None
            ),
        )
    )
    event_time = _business_now_naive()
    status_logs = [
        TaskItemStatusLog(
            task_type=task_type,
            task_id=task.id,
            document_id=task.document_id,
            order_item_id=item_id,
            from_status=previous_statuses.get(item_id),
            to_status=to_status,
            assignee_user_id=event_assignees.get(item_id) or assignee_user_id,
            operated_by=operated_by,
            operated_at=event_time,
            source="live",
        )
        for item_id in selected_ids
    ]
    added_logs = db.add_all(status_logs)
    if inspect.isawaitable(added_logs):
        await added_logs
    for item_id in selected_ids:
        states[item_id] = (to_status, progress)

    aggregate_status = _aggregate_task_status(
        task_type,
        [status for status, _ in states.values()],
    )
    aggregate_progress = round(
        sum(item_progress for _, item_progress in states.values()) / len(states)
    ) if states else progress
    task.status = aggregate_status
    task.progress_pct = max(0, min(100, aggregate_progress))
    if all(
        _is_completed_item_status(task_type, status)
        for status, _ in states.values()
    ):
        task.completed_at = _utc_now()
    elif aggregate_status != "cancelled":
        task.completed_at = None
    await db.flush()
    return selected_ids, states


async def _resolve_task_assignee(
    db: AsyncSession,
    task,
    requested_assigned_to,
) -> UUID:
    """Resolve and validate the task-level assignee before a status change.

    A missing request value means "keep the saved assignee" so existing API
    callers remain compatible. A supplied value must point to an active user;
    an empty task assignment is never allowed to pass the status precondition.
    """
    current_assignee = _coerce_uuid(getattr(task, "assigned_to", None))
    has_requested_assignee = requested_assigned_to not in (None, "")
    requested_uuid = (
        _coerce_uuid(requested_assigned_to)
        if has_requested_assignee
        else None
    )
    if has_requested_assignee and requested_uuid is None:
        raise ValueError("分配人无效，请重新选择")

    effective_assignee = requested_uuid or current_assignee
    if effective_assignee is None:
        raise ValueError("请先选择分配人，再变更任务状态")

    if has_requested_assignee:
        await validate_task_assignee(db, effective_assignee)

    return effective_assignee


async def _resolve_status_assignee(
    db: AsyncSession,
    task,
    requested_assigned_to,
    *,
    task_type: str,
    viewer: User | None,
) -> UUID | None:
    """Resolve the current login as the executor of selected item rows.

    ``task.assigned_to`` was the old whole-task owner. It is deliberately not
    consulted for real API requests anymore: visibility and execution belong to
    different layers, and a status request may only claim its checked rows.
    ``viewer is None`` is retained for legacy service-unit callers that do not
    construct an authenticated request context.
    """
    if viewer is None:
        return await _resolve_task_assignee(db, task, requested_assigned_to)
    if requested_assigned_to not in (None, ""):
        raise ValueError("状态变更不再设置整张任务负责人，请直接勾选要处理的订单明细")
    if can_assign_task(task_type, viewer):
        try:
            return await resolve_current_employee_user_id(db, viewer)
        except ValueError:
            # Stage managers/admins may operate selected rows without being an
            # employee themselves.  They do not claim an unassigned row unless
            # the login is actually bound to an active employee.
            return None
    return await resolve_current_employee_user_id(db, viewer)


def _reject_legacy_task_assignee_input(
    data: dict,
    task_type: str,
    viewer: User | None,
) -> None:
    """Prevent authenticated requests from reviving whole-task ownership."""
    if viewer is not None and "assigned_to" in data:
        raise ValueError(
            f"整张{TASK_TYPE_LABELS[task_type]}任务负责人已停用，请在订单上设置可见员工，"
            "或在任务处理卡中改派订单明细"
        )


async def _notify_task_assignee(
    db: AsyncSession,
    task_type: str,
    task,
    assigned_to: UUID,
) -> None:
    """Reuse the existing in-app task assignment notification semantics."""
    from app.services.notification_service import NotificationService

    number_field = {
        "design": "design_no",
        "production": "production_no",
        "installation": "installation_no",
    }[task_type]
    task_label = TASK_TYPE_LABELS[task_type]
    task_no = getattr(task, number_field)
    notif_svc = NotificationService(db)
    await notif_svc.create_system_notification(
        user_id=assigned_to,
        type_="task_assigned",
        title=f"{task_label}任务分配: {task_no}",
        content=f"您被分配了{task_label}任务 {getattr(task, 'project_name', '')}",
        link=f"/{task_type}-tasks/{task.id}",
    )


class DesignTaskService:
    def __init__(self, db: AsyncSession, viewer: User | None = None):
        self.db = db
        self.repo = DesignTaskRepository(db)
        self.viewer = viewer

    async def _to_dict(self, task) -> dict:
        d = DesignTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d["_task_type"] = "design"
        d = await _enrich_task_order(self.db, d, viewer=self.viewer) if self.viewer else await _enrich_task_order(self.db, d)
        d = enrich_task_dict_with_schedule_state(d)
        return add_task_contract_fields(d, "design")

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None,
                         order_item_id: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        if not can_view_outsource_tasks(self.viewer):
            outsourced = None
        tasks, total = await self.repo.list_tasks(
            skip=skip, limit=page_size, status=status, order_id=order_id,
            assigned_to=assigned_to, outsourced=outsourced,
            order_item_id=order_item_id,
            viewer=self.viewer,
        )
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "design", result, viewer=self.viewer), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict, operated_by: UUID | None = None) -> dict:
        _reject_legacy_task_assignee_input(data, "design", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("design", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能指定任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        data, item_ids = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=("confirmed", *ACTIVE_ORDER_STATUSES),
            task_label="设计",
            task_type="design",
        )
        data["design_no"] = await generate_design_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        if item_ids:
            await _sync_task_order_item_links(self.db, "design", task, item_ids)
        await record_task_event(
            self.db,
            "design",
            task,
            ACTION_CREATE,
            operated_by,
            changed_fields=list(data.keys()),
        )
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新设计任务: {task.design_no}",
                content=f"您被分配了设计任务 {task.project_name}",
                link=f"/design-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("设计任务不存在")
        _reject_legacy_task_assignee_input(data, "design", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("design", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能修改任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        old_assigned = task.assigned_to
        previous_legacy_item_id = _task_order_item_id(task)
        before = task_history_snapshot(task)
        data = normalize_task_schedule_data(
            data,
            current_start_at=task.planned_start_at,
            current_end_at=task.planned_end_at,
        )
        linked_item_ids: list[UUID] | None = None
        if "order_item_id" in data and "order_item_ids" in data:
            raise ValueError("不能同时提交订单明细编号和订单明细编号列表")
        if "order_item_ids" in data:
            linked_item_ids = await _validate_order_item_ids(
                self.db,
                task.document_id,
                data.pop("order_item_ids"),
                task_type="design",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            data["order_item_id"] = linked_item_ids[0] if linked_item_ids else None
        elif "order_item_id" in data:
            data["order_item_id"] = await _validate_order_item_id(
                self.db,
                task.document_id,
                data.get("order_item_id"),
                task_type="design",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            linked_item_ids = [data["order_item_id"]] if data["order_item_id"] else []
        if linked_item_ids is not None and previous_legacy_item_id is None:
            await _materialize_legacy_task_scope(self.db, "design", task)
        task = await self.repo.update(task, data)
        if linked_item_ids is not None:
            await _sync_task_order_item_links(
                self.db,
                "design",
                task,
                linked_item_ids,
                previous_legacy_item_id=previous_legacy_item_id,
            )
        await record_task_event(
            self.db,
            "design",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            changed_fields=list(data.keys()),
        )
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"设计任务分配: {task.design_no}",
                content=f"您被分配了设计任务 {task.project_name}",
                link=f"/design-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def reassign_items(
        self,
        task_id: UUID,
        order_item_ids: list[str],
        assignee_user_id: str | None,
        operated_by: UUID | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("设计任务不存在")
        before = task_history_snapshot(task)
        await _reassign_task_item_links(
            self.db,
            "design",
            task,
            order_item_ids,
            assignee_user_id,
            viewer=self.viewer,
        )
        await record_task_event(
            self.db,
            "design",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            reason="明细执行人改派" if assignee_user_id else "释放明细执行人",
            changed_fields=["order_item_assignees", "order_item_ids"],
        )
        await self.db.flush()
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(
        self,
        task_id: UUID,
        to_status: str,
        operated_by: UUID | None = None,
        reason: str | None = None,
        order_item_ids: list[str] | None = None,
        assigned_to: str | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("设计任务不存在")

        await _ensure_terminal_unlinked_task_is_read_only(self.db, "design", task)
        if not order_item_ids and _task_order_item_id(task) is None:
            raise ValueError("请先勾选要处理的订单明细")
        effective_assignee = await _resolve_status_assignee(
            self.db,
            task,
            assigned_to,
            task_type="design",
            viewer=self.viewer,
        )
        before = task_history_snapshot(task)
        try:
            selected_item_ids, states = await _apply_task_item_status_change(
                self.db,
                "design",
                task,
                to_status,
                order_item_ids,
                viewer=self.viewer,
                assignee_user_id=effective_assignee,
                operated_by=operated_by,
            )
            await record_task_event(
                self.db,
                "design",
                task,
                ACTION_STATUS_CHANGE,
                operated_by,
                before=before,
                reason=reason,
                changed_fields=[
                    "order_item_ids",
                    "item_status",
                    "status",
                    "progress_pct",
                ],
            )
            if task.document_id:
                from app.models.task import DesignTask

                for item_id in selected_item_ids:
                    item_status = states[item_id][0]
                    if (
                        _is_completed_item_status("design", item_status)
                        and await _item_stage_tasks_completed(
                            self.db,
                            task.document_id,
                            item_id,
                            DesignTask,
                            {"confirmed", "completed", "cancelled"},
                        )
                    ):
                        await _create_production_task_for_item(self.db, task, item_id)
                await _maybe_advance_order_stage(
                    self.db,
                    task.document_id,
                    "designing",
                    "in_production",
                    DesignTask,
                    {"confirmed", "completed", "cancelled"},
                    "所有订单明细的设计任务已完成，系统自动推进",
                    operated_by,
                )
                await _maybe_complete_order(self.db, task.document_id, operated_by)
            await _refresh_task_for_response(self.db, task)
            return await self._to_dict(task)
        except Exception:
            raise

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除设计任务，回退订单到确认状态。"""
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("设计任务不存在")

        doc_id = task.document_id
        design_ids = [task_id]
        prod_ids: list[UUID] = []
        inst_ids: list[UUID] = []
        await _clear_task_order_item_links(self.db, "design", design_ids)
        # Hard delete the task
        await self.db.delete(task)

        # Revert order to confirmed (pre-design state)
        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.models.task import InstallationTask, ProductionTask
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status in ("designing", "in_production", "in_installation"):
                # Cancel downstream auto-created tasks
                for model_cls in (ProductionTask, InstallationTask):
                    result = await self.db.execute(
                        select(model_cls).where(model_cls.document_id == doc_id)
                    )
                    for t in result.scalars().all():
                        if model_cls is ProductionTask:
                            prod_ids.append(t.id)
                        else:
                            inst_ids.append(t.id)
                        await _clear_task_order_item_links(
                            self.db,
                            "production" if model_cls is ProductionTask else "installation",
                            [t.id],
                        )
                        await self.db.delete(t)

                # Soft-delete acceptance if exists
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = _utc_now()

                # Revert order
                old_status = order.status
                order.status = "pending_confirm"
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                await order_svc.repo.create_status_log(doc_id, old_status, "pending_confirm",
                    "设计任务已被管理员删除，系统自动回退到待确认", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "design", design_ids)
        await _clear_outsource_source_refs(self.db, "production", prod_ids)
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

class ProductionTaskService:
    def __init__(self, db: AsyncSession, viewer: User | None = None):
        self.db = db
        self.repo = ProductionTaskRepository(db)
        self.viewer = viewer

    async def _to_dict(self, task) -> dict:
        d = ProductionTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d["_task_type"] = "production"
        d = await _enrich_task_order(self.db, d, viewer=self.viewer) if self.viewer else await _enrich_task_order(self.db, d)
        d = enrich_task_dict_with_schedule_state(d)
        return add_task_contract_fields(d, "production")

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None,
                         order_item_id: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        if not can_view_outsource_tasks(self.viewer):
            outsourced = None
        tasks, total = await self.repo.list_tasks(
            skip=skip, limit=page_size, status=status, order_id=order_id,
            assigned_to=assigned_to, outsourced=outsourced,
            order_item_id=order_item_id,
            viewer=self.viewer,
        )
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "production", result, viewer=self.viewer), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict, operated_by: UUID | None = None) -> dict:
        _reject_legacy_task_assignee_input(data, "production", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("production", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能指定任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        data, item_ids = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=ACTIVE_ORDER_STATUSES,
            task_label="制作",
            task_type="production",
        )
        data["production_no"] = await generate_production_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        if item_ids:
            await _sync_task_order_item_links(self.db, "production", task, item_ids)
        await record_task_event(
            self.db,
            "production",
            task,
            ACTION_CREATE,
            operated_by,
            changed_fields=list(data.keys()),
        )
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新制作任务: {task.production_no}",
                content=f"您被分配了制作任务 {task.project_name}",
                link=f"/production-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("制作任务不存在")
        _reject_legacy_task_assignee_input(data, "production", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("production", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能修改任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        old_assigned = task.assigned_to
        previous_legacy_item_id = _task_order_item_id(task)
        before = task_history_snapshot(task)
        data = normalize_task_schedule_data(
            data,
            current_start_at=task.planned_start_at,
            current_end_at=task.planned_end_at,
        )
        linked_item_ids: list[UUID] | None = None
        if "order_item_id" in data and "order_item_ids" in data:
            raise ValueError("不能同时提交订单明细编号和订单明细编号列表")
        if "order_item_ids" in data:
            linked_item_ids = await _validate_order_item_ids(
                self.db,
                task.document_id,
                data.pop("order_item_ids"),
                task_type="production",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            data["order_item_id"] = linked_item_ids[0] if linked_item_ids else None
        elif "order_item_id" in data:
            data["order_item_id"] = await _validate_order_item_id(
                self.db,
                task.document_id,
                data.get("order_item_id"),
                task_type="production",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            linked_item_ids = [data["order_item_id"]] if data["order_item_id"] else []
        if linked_item_ids is not None and previous_legacy_item_id is None:
            await _materialize_legacy_task_scope(self.db, "production", task)
        task = await self.repo.update(task, data)
        if linked_item_ids is not None:
            await _sync_task_order_item_links(
                self.db,
                "production",
                task,
                linked_item_ids,
                previous_legacy_item_id=previous_legacy_item_id,
            )
        await record_task_event(
            self.db,
            "production",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            changed_fields=list(data.keys()),
        )
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"制作任务分配: {task.production_no}",
                content=f"您被分配了制作任务 {task.project_name}",
                link=f"/production-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def reassign_items(
        self,
        task_id: UUID,
        order_item_ids: list[str],
        assignee_user_id: str | None,
        operated_by: UUID | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("制作任务不存在")
        before = task_history_snapshot(task)
        await _reassign_task_item_links(
            self.db,
            "production",
            task,
            order_item_ids,
            assignee_user_id,
            viewer=self.viewer,
        )
        await record_task_event(
            self.db,
            "production",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            reason="明细执行人改派" if assignee_user_id else "释放明细执行人",
            changed_fields=["order_item_assignees", "order_item_ids"],
        )
        await self.db.flush()
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(
        self,
        task_id: UUID,
        to_status: str,
        operated_by: UUID | None = None,
        reason: str | None = None,
        order_item_ids: list[str] | None = None,
        assigned_to: str | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("制作任务不存在")

        await _ensure_terminal_unlinked_task_is_read_only(self.db, "production", task)
        if not order_item_ids and _task_order_item_id(task) is None:
            raise ValueError("请先勾选要处理的订单明细")
        effective_assignee = await _resolve_status_assignee(
            self.db,
            task,
            assigned_to,
            task_type="production",
            viewer=self.viewer,
        )
        before = task_history_snapshot(task)
        try:
            selected_item_ids, states = await _apply_task_item_status_change(
                self.db,
                "production",
                task,
                to_status,
                order_item_ids,
                viewer=self.viewer,
                assignee_user_id=effective_assignee,
                operated_by=operated_by,
            )
            await record_task_event(
                self.db,
                "production",
                task,
                ACTION_STATUS_CHANGE,
                operated_by,
                before=before,
                reason=reason,
                changed_fields=[
                    "order_item_ids",
                    "item_status",
                    "status",
                    "progress_pct",
                ],
            )
            if task.document_id:
                from app.models.task import ProductionTask

                for item_id in selected_item_ids:
                    item_status = states[item_id][0]
                    if (
                        _is_completed_item_status("production", item_status)
                        and await _item_stage_tasks_completed(
                            self.db,
                            task.document_id,
                            item_id,
                            ProductionTask,
                            {"completed", "cancelled"},
                        )
                    ):
                        await _create_installation_task_for_item(self.db, task, item_id)
                await _maybe_advance_order_stage(
                    self.db,
                    task.document_id,
                    "in_production",
                    "in_installation",
                    ProductionTask,
                    {"completed", "cancelled"},
                    "所有订单明细的制作任务已完成，系统自动推进",
                    operated_by,
                )
                await _maybe_complete_order(self.db, task.document_id, operated_by)
            await _refresh_task_for_response(self.db, task)
            return await self._to_dict(task)
        except Exception:
            raise

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除制作任务，回退订单到设计中状态。"""
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("制作任务不存在")

        doc_id = task.document_id
        prod_ids = [task_id]
        inst_ids: list[UUID] = []
        await _clear_task_order_item_links(self.db, "production", prod_ids)
        await self.db.delete(task)

        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.models.task import InstallationTask
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status in ("in_production", "in_installation"):
                # Cancel downstream installation task
                result = await self.db.execute(
                    select(InstallationTask).where(InstallationTask.document_id == doc_id)
                )
                for t in result.scalars().all():
                    inst_ids.append(t.id)
                    await _clear_task_order_item_links(
                        self.db,
                        "installation",
                        [t.id],
                    )
                    await self.db.delete(t)

                # Soft-delete acceptance if exists
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = _utc_now()

                old_status = order.status
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                # 回退到设计中；若无设计任务则补建一个，保证看板设计栏有任务可跳转
                await order_svc._auto_create_design_task(order)
                order.status = "designing"
                await order_svc.repo.create_status_log(doc_id, old_status, "designing",
                    "制作任务已被管理员删除，系统自动回退", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "production", prod_ids)
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

class InstallationTaskService:
    def __init__(self, db: AsyncSession, viewer: User | None = None):
        self.db = db
        self.repo = InstallationTaskRepository(db)
        self.viewer = viewer

    async def _to_dict(self, task) -> dict:
        d = InstallationTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d["_task_type"] = "installation"
        d = await _enrich_task_order(self.db, d, viewer=self.viewer) if self.viewer else await _enrich_task_order(self.db, d)
        d = enrich_task_dict_with_schedule_state(d)
        return add_task_contract_fields(d, "installation")

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None,
                         order_item_id: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        if not can_view_outsource_tasks(self.viewer):
            outsourced = None
        tasks, total = await self.repo.list_tasks(
            skip=skip, limit=page_size, status=status, order_id=order_id,
            assigned_to=assigned_to, outsourced=outsourced,
            order_item_id=order_item_id,
            viewer=self.viewer,
        )
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "installation", result, viewer=self.viewer), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict, operated_by: UUID | None = None) -> dict:
        _reject_legacy_task_assignee_input(data, "installation", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("installation", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能指定任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        data, item_ids = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=ACTIVE_ORDER_STATUSES,
            task_label="安装",
            task_type="installation",
        )
        data["installation_no"] = await generate_installation_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        if item_ids:
            await _sync_task_order_item_links(self.db, "installation", task, item_ids)
        await record_task_event(
            self.db,
            "installation",
            task,
            ACTION_CREATE,
            operated_by,
            changed_fields=list(data.keys()),
        )
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新安装任务: {task.installation_no}",
                content=f"您被分配了安装任务 {task.project_name}",
                link=f"/installation-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("安装任务不存在")
        _reject_legacy_task_assignee_input(data, "installation", self.viewer)
        if "assigned_to" in data:
            if not can_assign_task("installation", self.viewer):
                raise ValueError("当前账号没有任务分配权限，不能修改任务负责人")
            if self.viewer is not None:
                data["assigned_to"] = await validate_task_assignee(
                    self.db, data.get("assigned_to")
                )
        old_assigned = task.assigned_to
        previous_legacy_item_id = _task_order_item_id(task)
        before = task_history_snapshot(task)
        data = normalize_task_schedule_data(
            data,
            current_start_at=task.planned_start_at,
            current_end_at=task.planned_end_at,
        )
        linked_item_ids: list[UUID] | None = None
        if "order_item_id" in data and "order_item_ids" in data:
            raise ValueError("不能同时提交订单明细编号和订单明细编号列表")
        if "order_item_ids" in data:
            linked_item_ids = await _validate_order_item_ids(
                self.db,
                task.document_id,
                data.pop("order_item_ids"),
                task_type="installation",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            data["order_item_id"] = linked_item_ids[0] if linked_item_ids else None
        elif "order_item_id" in data:
            data["order_item_id"] = await _validate_order_item_id(
                self.db,
                task.document_id,
                data.get("order_item_id"),
                task_type="installation",
                task_id=task.id,
                legacy_item_id=_task_order_item_id(task),
            )
            linked_item_ids = [data["order_item_id"]] if data["order_item_id"] else []
        if linked_item_ids is not None and previous_legacy_item_id is None:
            await _materialize_legacy_task_scope(self.db, "installation", task)
        task = await self.repo.update(task, data)
        if linked_item_ids is not None:
            await _sync_task_order_item_links(
                self.db,
                "installation",
                task,
                linked_item_ids,
                previous_legacy_item_id=previous_legacy_item_id,
            )
        await record_task_event(
            self.db,
            "installation",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            changed_fields=list(data.keys()),
        )
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"安装任务分配: {task.installation_no}",
                content=f"您被分配了安装任务 {task.project_name}",
                link=f"/installation-tasks/{task.id}",
            )
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def reassign_items(
        self,
        task_id: UUID,
        order_item_ids: list[str],
        assignee_user_id: str | None,
        operated_by: UUID | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("安装任务不存在")
        before = task_history_snapshot(task)
        await _reassign_task_item_links(
            self.db,
            "installation",
            task,
            order_item_ids,
            assignee_user_id,
            viewer=self.viewer,
        )
        await record_task_event(
            self.db,
            "installation",
            task,
            ACTION_UPDATE,
            operated_by,
            before=before,
            reason="明细执行人改派" if assignee_user_id else "释放明细执行人",
            changed_fields=["order_item_assignees", "order_item_ids"],
        )
        await self.db.flush()
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(
        self,
        task_id: UUID,
        to_status: str,
        operated_by: UUID | None = None,
        reason: str | None = None,
        order_item_ids: list[str] | None = None,
        assigned_to: str | None = None,
    ) -> dict:
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("安装任务不存在")

        await _ensure_terminal_unlinked_task_is_read_only(self.db, "installation", task)
        if not order_item_ids and _task_order_item_id(task) is None:
            raise ValueError("请先勾选要处理的订单明细")
        effective_assignee = await _resolve_status_assignee(
            self.db,
            task,
            assigned_to,
            task_type="installation",
            viewer=self.viewer,
        )
        before = task_history_snapshot(task)
        try:
            selected_item_ids, _states = await _apply_task_item_status_change(
                self.db,
                "installation",
                task,
                to_status,
                order_item_ids,
                viewer=self.viewer,
                assignee_user_id=effective_assignee,
                operated_by=operated_by,
            )
            await record_task_event(
                self.db,
                "installation",
                task,
                ACTION_STATUS_CHANGE,
                operated_by,
                before=before,
                reason=reason,
                changed_fields=[
                    "order_item_ids",
                    "item_status",
                    "status",
                    "progress_pct",
                ],
            )
            if task.document_id and selected_item_ids:
                await _maybe_complete_order(self.db, task.document_id, operated_by)
            await _refresh_task_for_response(self.db, task)
            return await self._to_dict(task)
        except Exception:
            raise

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除安装任务，回退订单到生产中状态。"""
        task = await self.repo.get_by_id(task_id, viewer=self.viewer)
        if not task:
            raise ValueError("安装任务不存在")

        doc_id = task.document_id
        inst_ids = [task_id]
        await _clear_task_order_item_links(self.db, "installation", inst_ids)
        await self.db.delete(task)
        # Make the deletion visible before rebuilding the previous stage. A
        # blank successor created by reopening a completed order is not work
        # itself; removing it must still leave the order in production.
        await self.db.flush()

        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status == "in_installation":
                # Soft-delete acceptance if exists. Deleting a task is a
                # rollback operation; it must never be interpreted as proof
                # that the order is complete, even when historical tasks are
                # all terminal.
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = _utc_now()

                old_status = order.status
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                # 回退到制作中，并重新打开历史制作明细，保证制作看板有任务可处理。
                await order_svc._auto_create_production_task(
                    order,
                    reopen_terminal=True,
                )
                order.status = "in_production"
                await order_svc.repo.create_status_log(doc_id, old_status, "in_production",
                    "安装任务已被管理员删除，系统自动回退", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

class AttachmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttachmentRepository(db)

    async def add_attachment(self, related_type: str, related_id: UUID, data: dict, uploaded_by: UUID | None = None) -> dict:
        data["related_type"] = related_type
        data["related_id"] = related_id
        data["uploaded_by"] = uploaded_by
        att = await self.repo.create(data)
        return _attachment_to_dict(att)

    async def list_attachments(self, related_type: str, related_id: UUID) -> list[dict]:
        atts = await self.repo.get_by_task(related_type, related_id)
        return [_attachment_to_dict(a) for a in atts]

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        return await self.repo.delete(attachment_id)
