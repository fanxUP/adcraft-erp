"""Order query tools for AI Assistant."""

from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry
from app.core.permissions import (
    PERM_ORDER_READ,
    PERM_ORDER_VIEW_PRICE,
    PERM_PAYMENT_READ,
    user_has_permission,
)


async def search_orders(db, user, keyword="", page=1, page_size=20, status=None, customer_id=None):
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type='order', viewer=user)
    cid = UUID(customer_id) if customer_id else None
    orders, total = await svc.list_all(page, page_size, status=status, customer_id=cid, keyword=keyword or None)
    return {"orders": orders, "total": total, "page": page, "page_size": page_size}


async def get_order_detail(db, user, order_id):
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type='order', viewer=user)
    order = await svc.get_by_id(UUID(order_id))
    if not order:
        return {"error": "订单不存在"}
    return order


async def get_order_progress(db, user, order_id):
    from app.services.business_document_service import BusinessDocumentService
    from app.services.payment_service import PaymentService
    from app.services.task_service import (
        DesignTaskService,
        InstallationTaskService,
        ProductionTaskService,
    )
    doc_svc = BusinessDocumentService(db, doc_type='order', viewer=user)
    order = await doc_svc.get_by_id(UUID(order_id))
    if not order:
        return {"error": "订单不存在"}
    oid = UUID(order_id)
    design_svc = DesignTaskService(db, viewer=user); dt, _ = await design_svc.list_tasks(page=1, page_size=50, order_id=str(oid))
    prod_svc = ProductionTaskService(db, viewer=user); pt, _ = await prod_svc.list_tasks(page=1, page_size=50, order_id=str(oid))
    install_svc = InstallationTaskService(db, viewer=user); it, _ = await install_svc.list_tasks(page=1, page_size=50, order_id=str(oid))
    result = {"order": order, "design_tasks": {"items": dt, "total": len(dt)},
            "production_tasks": {"items": pt, "total": len(pt)},
            "installation_tasks": {"items": it, "total": len(it)}}
    # Payment amounts are a separate sensitive channel.  The order-price
    # permission alone must not expose receipts, and payment-read alone must
    # not make order totals available through this tool.
    if user_has_permission(user, PERM_ORDER_VIEW_PRICE) and user_has_permission(user, PERM_PAYMENT_READ):
        pay_svc = PaymentService(db)
        payments, _ = await pay_svc.list_payments(page=1, page_size=50, order_id=oid, is_voided=False)
        total_paid = sum(float(p.get("amount", 0)) for p in payments)
        result.update({
            "payments": {"items": payments, "total": len(payments)},
            "total_paid": total_paid,
        })
    return result


def register_order_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(name="search_orders", description="搜索订单，支持按订单号/客户名称/状态筛选",
        parameters={"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索关键词"},
            "status": {"type": "string", "description": "订单状态"}, "customer_id": {"type": "string", "description": "客户ID"},
            "page": {"type": "integer", "description": "页码"}, "page_size": {"type": "integer", "description": "每页数量"}},
            "required": []},
        risk_level="level_1", required_permission=PERM_ORDER_READ, handler=search_orders))
    r.register(AiToolDefinition(name="get_order_detail", description="获取订单详细信息",
        parameters={"type": "object", "properties": {"order_id": {"type": "string", "description": "订单ID"}},
            "required": ["order_id"]},
        risk_level="level_1", required_permission=PERM_ORDER_READ, handler=get_order_detail))
    r.register(AiToolDefinition(name="get_order_progress", description="查询订单完整进度（设计/制作/安装/收款）",
        parameters={"type": "object", "properties": {"order_id": {"type": "string", "description": "订单ID"}},
            "required": ["order_id"]},
        risk_level="level_1", required_permission=PERM_ORDER_READ, handler=get_order_progress))
