"""跨模块共享的业务状态机定义。"""

from collections.abc import Mapping

Workflow = Mapping[str, tuple[str, ...]]

ORDER_WORKFLOW: Workflow = {
    "pending_confirm": ("confirmed", "cancelled"),
    "confirmed": ("designing", "cancelled"),
    "designing": ("in_production", "in_installation", "cancelled"),
    "in_production": ("designing", "in_installation", "cancelled"),
    "in_installation": (
        "designing",
        "in_production",
        "completed",
        "cancelled",
    ),
    "completed": (),
    "cancelled": (),
}

QUOTE_WORKFLOW: Workflow = {
    "draft": ("confirmed", "cancelled"),
    "confirmed": ("converted", "cancelled", "draft"),
    "cancelled": (),
    "converted": (),
}

CONTRACT_WORKFLOW: Workflow = {
    "draft": ("active", "completed"),
    "active": ("draft", "completed"),
    "completed": (),
}

ACCEPTANCE_WORKFLOW: Workflow = {
    "draft": ("pending",),
    "pending": ("accepted", "rejected"),
    "rejected": ("draft",),
}

DESIGN_TASK_WORKFLOW: Workflow = {
    "pending": ("designing", "cancelled"),
    "designing": ("pending_review", "pending", "cancelled"),
    "pending_review": ("confirmed", "revision", "cancelled"),
    "revision": ("designing", "pending_review", "cancelled"),
    "confirmed": ("cancelled",),
    "cancelled": (),
}

PRODUCTION_TASK_WORKFLOW: Workflow = {
    "pending": ("in_progress", "cancelled"),
    "in_progress": ("completed", "rework", "cancelled"),
    "rework": ("in_progress", "cancelled"),
    "completed": (),
    "cancelled": (),
}

INSTALLATION_TASK_WORKFLOW: Workflow = {
    "pending": ("assigned", "in_progress", "cancelled"),
    "assigned": ("in_progress", "pending", "cancelled"),
    "in_progress": ("pending_acceptance", "pending", "cancelled"),
    "pending_acceptance": ("completed", "in_progress", "cancelled"),
    "completed": (),
    "cancelled": (),
}

OUTSOURCE_TASK_WORKFLOW: Workflow = {
    "pending": ("in_progress",),
    "in_progress": ("completed",),
    "completed": (),
    "settled": (),
    "cancelled": (),
}


def allowed_targets(workflow: Workflow, current_status: str) -> tuple[str, ...]:
    return workflow.get(current_status, ())


def ensure_transition(
    workflow: Workflow,
    current_status: str,
    target_status: str,
) -> None:
    if target_status not in allowed_targets(workflow, current_status):
        raise ValueError(f"不允许从 {current_status} 流转到 {target_status}")
