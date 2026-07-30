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
        "pending_acceptance",
        "cancelled",
    ),
    "pending_acceptance": ("completed", "in_installation", "cancelled"),
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
    "pending": ("designing",),
    "designing": ("pending_review", "pending"),
    "pending_review": ("confirmed", "revision"),
    "revision": ("designing", "pending_review"),
    "confirmed": (),
    "cancelled": (),
}

PRODUCTION_TASK_WORKFLOW: Workflow = {
    "pending": ("in_progress",),
    "in_progress": ("rework", "completed"),
    "rework": ("in_progress",),
    "completed": (),
    "cancelled": (),
}

INSTALLATION_TASK_WORKFLOW: Workflow = {
    "pending": ("assigned", "in_progress"),
    "assigned": ("in_progress", "pending"),
    "in_progress": ("pending_acceptance", "pending"),
    "pending_acceptance": ("completed", "in_progress"),
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
