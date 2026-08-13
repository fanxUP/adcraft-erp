"""Quote draft generation, query and creation tools for AI Assistant."""

from uuid import UUID
from app.ai_assistant.tool_registry import ToolRegistry, AiToolDefinition
from app.services.quote_calculation import calculate_quote_item_values


AI_QUOTE_ITEM_FIELDS = (
    "item_name",
    "quantity",
    "unit",
    "unit_price",
    "width",
    "width_unit",
    "height",
    "height_unit",
    "pieces",
    "use_area",
    "other_fee",
    "material_process",
    "remark",
)

AI_QUOTE_ITEM_SCHEMA_PROPERTIES = {
    "item_name": {"type": "string", "description": "项目名称"},
    "quantity": {"type": "number", "description": "数量"},
    "unit": {"type": "string", "description": "单位"},
    "unit_price": {"type": "number", "description": "单价"},
    "product_id": {"type": "string", "description": "产品/材质/工艺组合ID"},
    "material_process": {"type": "string", "description": "产品/材质/工艺组合"},
    "width": {"type": "number", "description": "宽"},
    "width_unit": {"type": "string", "description": "宽单位: m/cm/mm"},
    "height": {"type": "number", "description": "高"},
    "height_unit": {"type": "string", "description": "高单位: m/cm/mm"},
    "pieces": {"type": "number", "description": "件数"},
    "use_area": {"type": "boolean", "description": "是否按面积计价"},
    "other_fee": {"type": "number", "description": "其他费用"},
    "remark": {"type": "string", "description": "备注"},
}


def _build_ai_quote_item(item: dict, sort_order: int) -> dict:
    """只保留常规报价支持的字段，金额统一交给业务服务重算。"""
    result = {
        field: item[field]
        for field in AI_QUOTE_ITEM_FIELDS
        if field in item and item[field] is not None
    }
    result.setdefault("item_name", "")
    result.setdefault("quantity", 1)
    result.setdefault("unit_price", 0)
    result["sort_order"] = sort_order
    if item.get("product_id"):
        result["product_id"] = UUID(str(item["product_id"]))
    return result


def _preview_ai_quote_item(item: dict) -> dict:
    normalized = _build_ai_quote_item(item, 0)
    values = calculate_quote_item_values(normalized)
    return {
        **normalized,
        "area": float(values["area"]),
        "subtotal": float(values["subtotal_amount"]),
    }


async def search_quotes(db, user, keyword="", page=1, page_size=20, status=None, customer_id=None):
    """Search existing quotes (not orders) with keyword/doc_no/customer/status."""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote")
    cid = UUID(customer_id) if customer_id else None
    quotes, total = await svc.list_all(page, page_size, status=status, customer_id=cid, keyword=keyword or None)
    return {"quotes": quotes, "total": total, "page": page, "page_size": page_size}


async def get_quote_detail(db, user, quote_id):
    """Get full detail of an existing quote (not order), including items and status."""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote")
    quote = await svc.get_by_id(UUID(quote_id))
    if not quote:
        return {"error": "报价单不存在"}
    return quote


async def create_quote_draft(db, user, customer_id, description, customer_name=""):
    """Generate a quote draft preview (does NOT save)."""
    try:
        from app.ai.ai_enhanced.llm_quote_assistant import LLMQuoteAssistant
        from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient
        ai_client = GatewayAIClient(db)
        assistant = LLMQuoteAssistant(db, ai_client)
        draft = await assistant.generate_quote_draft(description, customer_id)
        draft["_preview"] = True
        draft["_note"] = "此为报价草稿预览，尚未保存。"
        return draft
    except ImportError:
        return {"_preview": True, "_note": "预览模式", "description": description,
                "customer_id": customer_id, "customer_name": customer_name}
    except Exception as e:
        return {"_preview": True, "_note": f"AI报价暂不可用: {str(e)}", "description": description,
                "customer_id": customer_id, "customer_name": customer_name}


async def create_quote_confirmed(db, user, customer_id, project_name="", items=None,
                                 sales_user_id=None, remark=""):
    """Actually create a quote in the system (saves to database)."""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote")

    items_data = [
        _build_ai_quote_item(item, index)
        for index, item in enumerate(items or [])
    ]

    quote_data = {
        "customer_id": customer_id,
        "project_name": project_name or "新报价单",
        "items": items_data,
        "remark": remark or "",
    }
    if sales_user_id:
        quote_data["sales_user_id"] = sales_user_id

    quote = await svc.create(quote_data)
    return {
        "status": "created",
        "quote_id": quote["id"],
        "quote_no": quote.get("quote_no", ""),
        "customer_name": quote.get("customer_name", ""),
        "project_name": quote.get("project_name", ""),
        "total_amount": quote.get("total_amount", 0),
        "items_count": len(items_data),
        "note": "报价单 " + quote.get("quote_no", "") + " 已成功创建。",
    }


async def preview_quote_creation(db, user, customer_id, project_name="", items=None,
                                 sales_user_id=None, remark=""):
    """Build a deterministic preview without creating a quote."""
    preview_items = [
        _preview_ai_quote_item(item)
        for item in items or []
    ]
    total_amount = round(
        sum(item["subtotal"] for item in preview_items),
        2,
    )
    return {
        "action_label": "创建报价单",
        "customer_id": customer_id,
        "project_name": project_name or "新报价单",
        "items": preview_items,
        "items_count": len(preview_items),
        "total_amount": total_amount,
        "sales_user_id": sales_user_id or "",
        "remark": remark,
        "note": "确认后才会创建报价单。",
    }


async def add_quote_items(db, user, quote_id, items):
    """Add line items to an existing quote (does not create a new quote)."""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote")

    items_data = [
        _build_ai_quote_item(item, index)
        for index, item in enumerate(items or [])
    ]

    result = await svc.add_items(UUID(quote_id), items_data)
    return result


async def add_quote_items_preview(db, user, quote_id, items):
    """Preview adding line items to an existing quote (does NOT save)."""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote")
    quote = await svc.get_by_id(UUID(quote_id))
    if not quote:
        return {"error": "报价单不存在"}

    preview_items = [
        _preview_ai_quote_item(item)
        for item in items or []
    ]
    preview_total = round(
        sum(item["subtotal"] for item in preview_items),
        2,
    )

    return {
        "_preview": True,
        "_note": "此为新增项目预览，尚未保存到报价单。",
        "quote_id": quote_id,
        "quote_no": quote.get("quote_no", ""),
        "current_items": len(quote.get("items", [])),
        "new_items": preview_items,
        "new_items_total": preview_total,
    }


def register_quote_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(
        name="search_quotes",
        description="搜索已有报价单，支持按报价单号/客户名称/状态筛选（仅查询报价单，不包括订单）",
        parameters={"type": "object", "properties": {
            "keyword": {"type": "string", "description": "搜索关键词（报价单号/客户名称）"},
            "status": {"type": "string", "description": "报价单状态"},
            "customer_id": {"type": "string", "description": "客户ID"},
            "page": {"type": "integer", "description": "页码"},
            "page_size": {"type": "integer", "description": "每页数量"}},
            "required": []},
        risk_level="level_1",
        required_permission="quote:read",
        handler=search_quotes,
    ))
    r.register(AiToolDefinition(
        name="get_quote_detail",
        description="获取已有报价单的详细信息（含明细项）",
        parameters={"type": "object", "properties": {
            "quote_id": {"type": "string", "description": "报价单ID"}},
            "required": ["quote_id"]},
        risk_level="level_1",
        required_permission="quote:read",
        handler=get_quote_detail,
    ))
    r.register(AiToolDefinition(
        name="add_quote_items_preview",
        description="预览为报价单新增项目（不会保存），用户确认后再调用 add_quote_items 保存。当用户说【在这个报价单中加入/增加/添加】时使用此工具生成预览",
        parameters={"type": "object", "properties": {
            "quote_id": {"type": "string", "description": "报价单ID"},
            "items": {"type": "array", "description": "要添加的项目列表",
                "items": {"type": "object", "properties": AI_QUOTE_ITEM_SCHEMA_PROPERTIES,
                    "required": ["item_name", "quantity", "unit_price"]}}},
            "required": ["quote_id", "items"]},
        risk_level="level_2",
        required_permission="quote:read",
        handler=add_quote_items_preview,
    ))
    r.register(AiToolDefinition(
        name="add_quote_items",
        description="确认后为报价单新增项目（实际保存到数据库）。用户确认预览后调用此工具",
        parameters={"type": "object", "properties": {
            "quote_id": {"type": "string", "description": "报价单ID"},
            "items": {"type": "array", "description": "要添加的项目列表",
                "items": {"type": "object", "properties": AI_QUOTE_ITEM_SCHEMA_PROPERTIES,
                    "required": ["item_name", "quantity", "unit_price"]}}},
            "required": ["quote_id", "items"]},
        risk_level="level_3",
        required_permission="quote:update",
        requires_confirmation=True,
        preview_handler=add_quote_items_preview,
        handler=add_quote_items,
    ))
    r.register(AiToolDefinition(
        name="create_quote_draft",
        description="根据客户需求生成全新报价草稿预览（不保存，仅用于用户没有指定报价单时创建新报价）",
        parameters={"type": "object", "properties": {
            "customer_id": {"type": "string", "description": "客户ID"},
            "description": {"type": "string", "description": "报价需求描述"},
            "customer_name": {"type": "string", "description": "客户名称"}},
            "required": ["customer_id", "description"]},
        risk_level="level_2",
        required_permission="quote:create",
        handler=create_quote_draft,
    ))
    r.register(AiToolDefinition(
        name="create_quote_confirmed",
        description="确认后创建全新报价单（实际保存到数据库，用于创建新报价，不是在已有报价单上加项目）",
        parameters={"type": "object", "properties": {
            "customer_id": {"type": "string", "description": "客户ID"},
            "project_name": {"type": "string", "description": "项目名称"},
            "items": {"type": "array", "description": "报价明细项",
                "items": {"type": "object", "properties": AI_QUOTE_ITEM_SCHEMA_PROPERTIES,
                    "required": ["item_name", "quantity", "unit_price"]}},
            "sales_user_id": {"type": "string", "description": "销售员用户ID"},
            "remark": {"type": "string", "description": "报价单备注"}},
            "required": ["customer_id", "items"]},
        risk_level="level_3",
        required_permission="quote:create",
        requires_confirmation=True,
        preview_handler=preview_quote_creation,
        handler=create_quote_confirmed,
    ))
