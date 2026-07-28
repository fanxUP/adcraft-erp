"""Customer query tools for AI Assistant."""

from uuid import UUID
from app.ai_assistant.tool_registry import ToolRegistry, AiToolDefinition


async def search_customers(db, user, keyword="", page=1, page_size=20):
    from app.services.customer_service import CustomerService
    svc = CustomerService(db)
    customers, total = await svc.list_customers(page, page_size, keyword=keyword or None)
    return {"customers": customers, "total": total, "page": page, "page_size": page_size}


async def get_customer_detail(db, user, customer_id):
    from app.services.customer_service import CustomerService
    svc = CustomerService(db)
    customer = await svc.get_customer(UUID(customer_id))
    if not customer:
        return {"error": "客户不存在"}
    return customer


async def get_customer_receivables(db, user, customer_id):
    from app.services.payment_service import PaymentService
    from app.services.business_document_service import BusinessDocumentService
    from app.services.customer_service import CustomerService
    pay_svc = PaymentService(db)
    payments, _ = await pay_svc.list_payments(page=1, page_size=999, customer_id=UUID(customer_id), is_voided=False)
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    doc_svc = BusinessDocumentService(db, doc_type='order')
    orders, _ = await doc_svc.list_all(page=1, page_size=999, customer_id=UUID(customer_id))
    cust_svc = CustomerService(db)
    customer = await cust_svc.get_customer(UUID(customer_id))
    return {"customer_name": customer.get("name") if customer else "未知", "total_orders": len(orders),
            "total_paid": total_paid, "payment_count": len(payments)}


def register_customer_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(name="search_customers", description="搜索客户，支持按客户名称/联系人/手机号关键词查询",
        parameters={"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索关键词"},
            "page": {"type": "integer", "description": "页码"}, "page_size": {"type": "integer", "description": "每页数量"}},
            "required": []},
        risk_level="level_1", required_permission="customer:read", handler=search_customers))
    r.register(AiToolDefinition(name="get_customer_detail", description="获取客户详细信息",
        parameters={"type": "object", "properties": {"customer_id": {"type": "string", "description": "客户ID"}},
            "required": ["customer_id"]},
        risk_level="level_1", required_permission="customer:read", handler=get_customer_detail))
    r.register(AiToolDefinition(name="get_customer_receivables", description="查询客户欠款/应收余额",
        parameters={"type": "object", "properties": {"customer_id": {"type": "string", "description": "客户ID"}},
            "required": ["customer_id"]},
        risk_level="level_1", required_permission="customer:read", handler=get_customer_receivables))
