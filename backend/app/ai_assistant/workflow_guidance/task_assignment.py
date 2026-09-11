"""Helpers for the item-level execution ownership model."""


_TERMINAL_ITEM_STATUSES = {"confirmed", "completed", "cancelled"}


def has_unassigned_task_items(task: dict) -> bool:
    """Return whether a task has active linked items without an executor.

    Current task snapshots always include ``order_item_states``.  The
    fallback to ``assigned_to`` keeps old, hand-built guidance snapshots
    readable while ensuring live snapshots no longer treat the legacy
    task-level owner as the source of truth.
    """
    if "order_item_states" not in task:
        return not task.get("assigned_to")

    states = task.get("order_item_states")
    if not isinstance(states, dict):
        return False
    return any(
        isinstance(state, dict)
        and not state.get("assignee_user_id")
        and state.get("status") not in _TERMINAL_ITEM_STATUSES
        for state in states.values()
    )
