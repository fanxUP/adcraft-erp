"""Shared response helpers for workflow guidance."""

from app.ai_assistant.page_capabilities import validate_page_action_target
from app.domain.workflows import allowed_targets

from .order_progress import attach_order_overview


def action(
    label: str,
    page: str,
    path: str,
    *,
    target_status: str | None = None,
    target_key: str | None = None,
) -> dict:
    result = {"label": label, "target_page": page, "target_path": path}
    if target_status:
        result["target_status"] = target_status
    if target_key:
        validate_page_action_target(target_key, path)
        result["target_key"] = target_key
    return result


def guidance_result(
    snapshot: dict,
    step: str,
    blockers: list[str],
    next_action: dict | None,
    completion_signal: str,
    workflow,
) -> dict:
    status = str(snapshot.get("status") or "")
    result = {
        "business_type": snapshot.get("business_type"),
        "business_id": snapshot.get("business_id"),
        "current_status": status,
        "current_step": step,
        "blockers": blockers,
        "next_action": next_action,
        "completion_signal": completion_signal,
        "allowed_next_statuses": list(allowed_targets(workflow, status)),
    }
    if snapshot.get("business_type") == "order":
        attach_order_overview(result, snapshot)
    return result


def unknown_guidance(snapshot: dict, fallback_path: str) -> dict:
    result = {
        "business_type": snapshot.get("business_type"),
        "business_id": snapshot.get("business_id"),
        "current_status": str(snapshot.get("status") or ""),
        "current_step": "状态待核实",
        "blockers": ["当前状态不在系统标准流程中，请先核实数据"],
        "next_action": action("查看业务详情", "业务详情", fallback_path),
        "completion_signal": "确认业务状态与系统标准流程一致",
        "allowed_next_statuses": [],
    }
    if snapshot.get("business_type") == "order":
        attach_order_overview(result, snapshot)
    return result
