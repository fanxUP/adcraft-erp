"""Installation task tools for AI Assistant."""

from uuid import UUID
from datetime import datetime
from app.ai_assistant.tool_registry import ToolRegistry, AiToolDefinition


async def create_installation_task_draft(db, user, order_id="", customer_name="", project_name="",
                                         install_address="", scheduled_date="", assigned_to="", notes=""):
    from app.services.business_document_service import BusinessDocumentService
    order = None
    if order_id:
        doc_svc = BusinessDocumentService(db, doc_type='order')
        order = await doc_svc.get_by_id(UUID(order_id))
    return {
        "action": "create_installation_task", "action_label": "创建安装任务", "risk_level": "level_2",
        "fields": {
            "order_id": order_id,
            "customer_name": customer_name or (order.get("customer_name", "") if order else ""),
            "project_name": project_name or (order.get("project_name", "") if order else ""),
            "install_address": install_address or (order.get("install_address", "") if order else ""),
            "scheduled_date": scheduled_date or datetime.now().strftime("%Y-%m-%d"),
            "assigned_to": assigned_to or "",
            "notes": notes or "",
        },
        "note": "此为草稿预览，尚未保存。确认后将创建安装任务。",
    }


async def create_installation_task_confirmed(db, user, order_id, customer_name="", project_name="",
                                             install_address="", scheduled_date="", assigned_to="", notes="",
                                             business_type=None, business_id=None):
    from app.services.task_service import InstallationTaskService
    data = {
        "document_id": UUID(order_id) if order_id else None,
        "project_name": project_name, "customer_name": customer_name,
        "install_address": install_address,
        "assigned_to": UUID(assigned_to) if assigned_to else None,
        "notes": notes, "business_type": business_type,
        "business_id": UUID(business_id) if business_id else None,
    }
    if scheduled_date:
        try:
            data["scheduled_date"] = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    svc = InstallationTaskService(db)
    task = await svc.create_task(data)
    return {"status": "created", "task": task}


def register_installation_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(name="create_installation_task_draft", description="生成安装任务草稿预览（不保存）",
        parameters={"type": "object", "properties": {
            "order_id": {"type": "string", "description": "订单ID"},
            "customer_name": {"type": "string", "description": "客户名称"},
            "project_name": {"type": "string", "description": "项目名称"},
            "install_address": {"type": "string", "description": "安装地址"},
            "scheduled_date": {"type": "string", "description": "计划安装日期"},
            "assigned_to": {"type": "string", "description": "安装人员ID"},
            "notes": {"type": "string", "description": "备注"}}, "required": []},
        risk_level="level_2", required_permission="customer:read", handler=create_installation_task_draft))
    r.register(AiToolDefinition(name="create_installation_task_confirmed", description="确认后创建安装任务",
        parameters={"type": "object", "properties": {
            "order_id": {"type": "string", "description": "订单ID"},
            "customer_name": {"type": "string", "description": "客户名称"},
            "project_name": {"type": "string", "description": "项目名称"},
            "install_address": {"type": "string", "description": "安装地址"},
            "scheduled_date": {"type": "string", "description": "计划安装日期"},
            "assigned_to": {"type": "string", "description": "安装人员ID"},
            "notes": {"type": "string", "description": "备注"}}, "required": ["order_id"]},
        risk_level="level_3", required_permission="customer:read", requires_confirmation=True,
        handler=create_installation_task_confirmed))
