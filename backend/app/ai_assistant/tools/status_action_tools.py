"""AI 安全状态推进工具。

LLM 只能提出候选状态；服务端使用统一状态机校验，并在确认执行时
重新读取当前状态，防止过期预览覆盖后来发生的业务变更。
"""

from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry
from app.domain.workflows import ORDER_WORKFLOW, allowed_targets


ORDER_STATUS_LABELS = {
    "pending_confirm": "待确认",
    "confirmed": "已确认",
    "designing": "设计中",
    "in_production": "生产中",
    "in_installation": "安装中",
    "completed": "已完成",
    "cancelled": "已取消",
}

ORDER_TRANSITION_EFFECTS = {
    "designing": ["进入设计阶段，请确保已创建设计任务"],
    "in_production": ["创建或衔接生产任务"],
    "in_installation": ["创建或衔接安装任务"],
    "completed": ["订单完结；如有欠款将生成收款提醒"],
    "cancelled": ["订单移入回收站"],
}


async def _get_order(db, business_id: str) -> dict:
    from app.services.business_document_service import BusinessDocumentService

    order = await BusinessDocumentService(db, doc_type="order").get_by_id(
        UUID(business_id),
    )
    if not order:
        raise ValueError("订单不存在")
    return order


async def preview_order_status_change(
    db,
    user,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    order = await _get_order(db, business_id)
    live_status = order.get("status", "")
    if live_status != current_status:
        raise ValueError(
            f"订单状态已变化，当前为「{ORDER_STATUS_LABELS.get(live_status, live_status)}」，"
            "请重新获取流程建议",
        )
    if target_status not in allowed_targets(ORDER_WORKFLOW, live_status):
        raise ValueError(f"不允许从 {live_status} 流转到 {target_status}")

    return {
        "action_label": "推进订单状态",
        "business_type": "order",
        "business_id": business_id,
        "business_no": order.get("doc_no", ""),
        "project_name": order.get("project_name", ""),
        "current_status": live_status,
        "current_status_label": ORDER_STATUS_LABELS.get(live_status, live_status),
        "target_status": target_status,
        "target_status_label": ORDER_STATUS_LABELS.get(target_status, target_status),
        "reason": reason,
        "effects": ORDER_TRANSITION_EFFECTS.get(target_status, []),
        "note": "确认后才会执行；执行前系统会再次核验订单状态和权限。",
    }


async def execute_order_status_change(
    db,
    user,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    from app.services.business_document_service import BusinessDocumentService

    service = BusinessDocumentService(db, doc_type="order")
    order = await service.get_by_id(UUID(business_id))
    if not order:
        raise ValueError("订单不存在")
    live_status = order.get("status", "")
    if live_status != current_status:
        raise ValueError(
            f"订单状态已变化，当前为「{ORDER_STATUS_LABELS.get(live_status, live_status)}」，"
            "原操作已停止",
        )

    updated = await service.change_status(
        UUID(business_id),
        target_status,
        reason or "AI 助手确认执行",
        user.id,
    )
    return {
        "status": "updated",
        "business_type": "order",
        "business_id": business_id,
        "business_no": updated.get("doc_no", ""),
        "previous_status": current_status,
        "current_status": updated.get("status", target_status),
        "message": (
            f"订单状态已从「{ORDER_STATUS_LABELS.get(current_status, current_status)}」"
            f"推进到「{ORDER_STATUS_LABELS.get(target_status, target_status)}」"
        ),
    }


def register_status_action_tools():
    ToolRegistry().register(AiToolDefinition(
        name="change_order_status",
        description=(
            "根据当前流程推进订单状态。必须使用流程导航返回的当前状态和允许的目标状态；"
            "系统先展示影响预览，用户确认后才执行。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "business_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "订单ID",
                },
                "current_status": {
                    "type": "string",
                    "enum": list(ORDER_WORKFLOW),
                    "description": "流程导航核验出的当前状态",
                },
                "target_status": {
                    "type": "string",
                    "enum": list(ORDER_WORKFLOW),
                    "description": "流程导航允许的目标状态",
                },
                "reason": {
                    "type": "string",
                    "maxLength": 500,
                    "description": "状态变更原因",
                },
            },
            "required": ["business_id", "current_status", "target_status"],
            "additionalProperties": False,
        },
        risk_level="level_3",
        required_permission="order:change_status",
        requires_confirmation=True,
        preview_handler=preview_order_status_change,
        handler=execute_order_status_change,
    ))
