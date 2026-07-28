"""Task query tools for AI Assistant."""

from app.ai_assistant.tool_registry import ToolRegistry, AiToolDefinition


async def list_today_tasks(db, user, task_type=None):
    from app.services.task_service import DesignTaskService, ProductionTaskService, InstallationTaskService
    result = {}
    if not task_type or task_type == "design":
        svc = DesignTaskService(db); t, n = await svc.list_tasks(page=1, page_size=50)
        result["design_tasks"] = {"items": t, "total": n}
    if not task_type or task_type == "production":
        svc = ProductionTaskService(db); t, n = await svc.list_tasks(page=1, page_size=50)
        result["production_tasks"] = {"items": t, "total": n}
    if not task_type or task_type == "installation":
        svc = InstallationTaskService(db); t, n = await svc.list_tasks(page=1, page_size=50)
        result["installation_tasks"] = {"items": t, "total": n}
    return result


def register_task_tools():
    r = ToolRegistry()
    r.register(AiToolDefinition(name="list_today_tasks", description="查询今日的设计/制作/安装任务列表",
        parameters={"type": "object", "properties": {
            "task_type": {"type": "string", "description": "任务类型", "enum": ["design", "production", "installation"]}},
            "required": []},
        risk_level="level_1", required_permission="customer:read", handler=list_today_tasks))
