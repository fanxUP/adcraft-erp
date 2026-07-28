"""Finance/debt query tools for AI Assistant."""

from uuid import UUID
from app.ai_assistant.tool_registry import ToolRegistry, AiToolDefinition


async def get_customer_receivables(db, user, customer_id):
    from app.services.payment_service import PaymentService
    from app.services.business_document_service import BusinessDocumentService
    pay_svc = PaymentService(db)
    payments, _ = await pay_svc.list_payments(page=1, page_size=999, customer_id=UUID(customer_id), is_voided=False)
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    doc_svc = BusinessDocumentService(db, doc_type='order')
    orders, order_total = await doc_svc.list_all(page=1, page_size=999, customer_id=UUID(customer_id))
    total_order_amount = sum(float(o.get("total_amount", o.get("subtotal_amount", 0))) for o in orders)
    receivable = max(0, total_order_amount - total_paid)
    return {"customer_id": customer_id, "total_orders": order_total,
            "total_order_amount": total_order_amount, "total_paid": total_paid,
            "receivable_balance": receivable, "payment_count": len(payments)}


def register_finance_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(name="get_customer_receivables", description="查询客户的欠款余额（应收 - 已收）",
        parameters={"type": "object", "properties": {"customer_id": {"type": "string", "description": "客户ID"}},
            "required": ["customer_id"]},
        risk_level="level_1", required_permission="customer:read", handler=get_customer_receivables))
