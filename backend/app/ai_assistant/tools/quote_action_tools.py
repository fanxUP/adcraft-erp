"""报价确认与转订单的 AI 安全操作工具。"""

from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry


QUOTE_STATUS_LABELS = {
    "draft": "草稿",
    "confirmed": "已确认",
    "converted": "已转换",
    "cancelled": "已取消",
    "pending_confirm": "订单待确认",
}


async def _get_quote_service_and_detail(db, business_id: str):
    from app.services.business_document_service import BusinessDocumentService

    service = BusinessDocumentService(db, doc_type="quote")
    quote = await service.get_by_id(UUID(business_id))
    if quote:
        return service, quote

    # 报价转订单后同一条单据的 doc_type 会变为 order，get_by_id 按 quote 过滤
    # 查不到，这里直接按 ID 定位单据，给出明确提示而不是报"不存在"
    from sqlalchemy import select

    from app.models.business_document import BusinessDocument

    result = await db.execute(
        select(BusinessDocument).where(BusinessDocument.id == UUID(business_id))
    )
    doc = result.scalar_one_or_none()
    if doc is not None and doc.doc_type == "order":
        raise ValueError(f"该报价已转为订单 {doc.doc_no}，请勿重复操作")
    raise ValueError("报价单不存在")


def _ensure_live_status(
    quote: dict,
    expected_status: str,
    *,
    stale_message: str,
) -> None:
    live_status = str(quote.get("status") or "")
    if live_status != expected_status:
        raise ValueError(
            "报价单状态已变化，当前为"
            f"「{QUOTE_STATUS_LABELS.get(live_status, live_status)}」，{stale_message}",
        )


async def preview_quote_confirmation(
    db,
    user,
    business_id: str,
    current_status: str,
):
    _, quote = await _get_quote_service_and_detail(db, business_id)
    _ensure_live_status(
        quote,
        current_status,
        stale_message="请重新获取流程建议",
    )
    if current_status != "draft":
        raise ValueError("只有草稿报价单可以确认")
    return {
        "action_label": "确认报价单",
        "business_type": "quote",
        "business_id": business_id,
        "business_no": quote.get("doc_no", ""),
        "project_name": quote.get("project_name", ""),
        "current_status": current_status,
        "current_status_label": "草稿",
        "target_status": "confirmed",
        "target_status_label": "已确认",
        "effects": ["报价内容将锁定为已确认状态", "后续可转换为正式订单"],
        "note": "确认后才会执行；执行前系统会再次核验报价状态和权限。",
    }


async def execute_quote_confirmation(
    db,
    user,
    business_id: str,
    current_status: str,
):
    service, quote = await _get_quote_service_and_detail(db, business_id)
    _ensure_live_status(quote, current_status, stale_message="原操作已停止")
    if current_status != "draft":
        raise ValueError("只有草稿报价单可以确认")
    updated = await service.change_status(
        UUID(business_id),
        "confirmed",
        "AI 助手确认执行",
        user.id,
    )
    return {
        "status": "updated",
        "business_type": "quote",
        "business_id": business_id,
        "business_no": updated.get("doc_no", ""),
        "previous_status": current_status,
        "current_status": updated.get("status", "confirmed"),
        "message": "报价单已确认，可以继续转换为正式订单",
    }


async def preview_quote_conversion(
    db,
    user,
    business_id: str,
    current_status: str,
):
    _, quote = await _get_quote_service_and_detail(db, business_id)
    _ensure_live_status(
        quote,
        current_status,
        stale_message="请重新获取流程建议",
    )
    if current_status != "confirmed":
        raise ValueError("只有已确认的报价单可以转订单")
    return {
        "action_label": "报价转正式订单",
        "business_type": "quote",
        "business_id": business_id,
        "business_no": quote.get("doc_no", ""),
        "project_name": quote.get("project_name", ""),
        "current_status": current_status,
        "current_status_label": "已确认",
        "target_status": "converted",
        "target_status_label": "正式订单",
        "effects": [
            "报价单将转换为正式订单并生成订单编号",
            "原业务记录和关联明细会继续保留",
        ],
        "note": "确认后才会执行；执行前系统会再次核验报价状态和转换权限。",
    }


async def execute_quote_conversion(
    db,
    user,
    business_id: str,
    current_status: str,
):
    service, quote = await _get_quote_service_and_detail(db, business_id)
    _ensure_live_status(quote, current_status, stale_message="原操作已停止")
    if current_status != "confirmed":
        raise ValueError("只有已确认的报价单可以转订单")
    order = await service.convert_doc_type(UUID(business_id), "order", user.id)
    return {
        "status": "converted",
        "business_type": "order",
        "business_id": business_id,
        "business_no": order.get("doc_no", ""),
        "previous_status": current_status,
        "current_status": order.get("status", "pending_confirm"),
        "message": f"报价单已转换为正式订单 {order.get('doc_no', '')}",
    }


def _quote_action_parameters(description: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "business_id": {
                "type": "string",
                "format": "uuid",
                "description": "报价单ID",
            },
            "current_status": {
                "type": "string",
                "description": description,
            },
        },
        "required": ["business_id", "current_status"],
        "additionalProperties": False,
    }


def register_quote_action_tools():
    registry = ToolRegistry()
    registry.register(AiToolDefinition(
        name="confirm_quote",
        description="确认草稿报价单。系统先展示预览，用户确认后才执行。",
        parameters=_quote_action_parameters("必须为流程导航核验出的 draft"),
        risk_level="level_3",
        required_permission="quote:confirm",
        requires_confirmation=True,
        preview_handler=preview_quote_confirmation,
        handler=execute_quote_confirmation,
    ))
    registry.register(AiToolDefinition(
        name="convert_quote_to_order",
        description="将已确认报价单转换为正式订单。系统先展示影响预览，用户确认后才执行。",
        parameters=_quote_action_parameters("必须为流程导航核验出的 confirmed"),
        risk_level="level_3",
        required_permission="quote:convert",
        requires_confirmation=True,
        preview_handler=preview_quote_conversion,
        handler=execute_quote_conversion,
    ))
