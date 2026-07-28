"""验收单的 AI 安全状态推进工具。"""

from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry
from app.domain.workflows import ACCEPTANCE_WORKFLOW, allowed_targets


ACCEPTANCE_STATUS_LABELS = {
    "draft": "草稿",
    "pending": "待验收",
    "accepted": "已通过",
    "rejected": "已驳回",
}


def _validate_acceptance_transition(
    acceptance: dict,
    current_status: str,
    target_status: str,
    reason: str,
    *,
    stale_message: str,
) -> None:
    live_status = str(acceptance.get("status") or "")
    if live_status != current_status:
        raise ValueError(
            "验收单状态已变化，当前为"
            f"「{ACCEPTANCE_STATUS_LABELS.get(live_status, live_status)}」，"
            f"{stale_message}",
        )
    if target_status not in allowed_targets(ACCEPTANCE_WORKFLOW, live_status):
        raise ValueError(f"不允许从 {live_status} 流转到 {target_status}")

    items = acceptance.get("items") or []
    if target_status == "pending" and not items:
        raise ValueError("验收单尚无验收明细，不能提交")
    if target_status == "accepted":
        unfinished = [
            item
            for item in items
            if item.get("item_status") not in ("accepted", "conditional")
        ]
        if unfinished:
            raise ValueError(f"仍有 {len(unfinished)} 项验收明细未确认")
    if target_status == "rejected" and not reason.strip():
        raise ValueError("驳回验收时必须填写原因")


async def _get_acceptance(db, business_id: str) -> tuple[object, dict]:
    from app.services.acceptance_service import AcceptanceService

    service = AcceptanceService(db)
    acceptance = await service.get_detail(UUID(business_id))
    return service, acceptance


async def preview_acceptance_status_change(
    db,
    user,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    _, acceptance = await _get_acceptance(db, business_id)
    _validate_acceptance_transition(
        acceptance,
        current_status,
        target_status,
        reason,
        stale_message="请重新获取流程建议",
    )
    effects = [
        f"验收单将进入「{ACCEPTANCE_STATUS_LABELS.get(target_status, target_status)}」",
    ]
    if target_status == "accepted":
        effects.append("关联订单将自动完成")
    elif target_status == "rejected":
        effects.append("关联订单将回退到安装中")
    return {
        "action_label": "推进验收状态",
        "business_type": "acceptance",
        "business_id": business_id,
        "business_no": acceptance.get("acceptance_no", ""),
        "project_name": acceptance.get("project_name", ""),
        "current_status": current_status,
        "current_status_label": ACCEPTANCE_STATUS_LABELS.get(
            current_status,
            current_status,
        ),
        "target_status": target_status,
        "target_status_label": ACCEPTANCE_STATUS_LABELS.get(
            target_status,
            target_status,
        ),
        "reason": reason,
        "effects": effects,
        "note": "确认后才会执行；执行前系统会再次核验验收明细、状态和权限。",
    }


async def execute_acceptance_status_change(
    db,
    user,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    service, acceptance = await _get_acceptance(db, business_id)
    _validate_acceptance_transition(
        acceptance,
        current_status,
        target_status,
        reason,
        stale_message="原操作已停止",
    )
    updated = await service.change_status(
        UUID(business_id),
        target_status,
        operated_by=user.id,
        reason=reason,
    )
    return {
        "status": "updated",
        "business_type": "acceptance",
        "business_id": business_id,
        "business_no": updated.get("acceptance_no", ""),
        "previous_status": current_status,
        "current_status": updated.get("status", target_status),
        "message": (
            "验收单状态已从"
            f"「{ACCEPTANCE_STATUS_LABELS.get(current_status, current_status)}」"
            f"推进到「{ACCEPTANCE_STATUS_LABELS.get(target_status, target_status)}」"
        ),
    }


def register_acceptance_action_tools():
    ToolRegistry().register(AiToolDefinition(
        name="change_acceptance_status",
        description=(
            "根据流程导航推进验收单状态。通过验收会联动订单完成，驳回会联动订单"
            "回退安装；系统先展示影响预览，用户确认后才执行。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "business_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "验收单ID",
                },
                "current_status": {
                    "type": "string",
                    "enum": list(ACCEPTANCE_WORKFLOW),
                    "description": "流程导航核验出的当前状态",
                },
                "target_status": {
                    "type": "string",
                    "enum": list(ACCEPTANCE_WORKFLOW),
                    "description": "流程导航允许的目标状态",
                },
                "reason": {
                    "type": "string",
                    "maxLength": 500,
                    "description": "状态变更原因；驳回时必填",
                },
            },
            "required": ["business_id", "current_status", "target_status"],
            "additionalProperties": False,
        },
        risk_level="level_3",
        required_permission="acceptance:change_status",
        requires_confirmation=True,
        preview_handler=preview_acceptance_status_change,
        handler=execute_acceptance_status_change,
    ))
