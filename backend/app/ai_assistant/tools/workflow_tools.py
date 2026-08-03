"""Read-only AI tool for resolving the next step of a live business record."""

from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry
from app.ai_assistant.workflow_guidance import build_workflow_guidance


def _require_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("业务ID格式不正确") from exc


async def _load_order_snapshot(db, user, business_id: str) -> dict:
    from app.ai_assistant.tools.order_tools import get_order_progress
    from app.services.acceptance_service import AcceptanceService

    progress = await get_order_progress(db, user, business_id)
    if progress.get("error"):
        raise ValueError(progress["error"])
    order = progress["order"]
    acceptances = []
    if order.get("status") == "pending_acceptance":
        acceptance_service = AcceptanceService(db)
        acceptance_summaries, _ = await acceptance_service.list_acceptances(
            page=1,
            page_size=20,
            document_id=business_id,
        )
        if acceptance_summaries:
            detail = await acceptance_service.get_detail(
                _require_uuid(str(acceptance_summaries[0]["id"]))
            )
            acceptances = [detail]
    return {
        **order,
        "business_type": "order",
        "business_id": business_id,
        "design_tasks": progress.get("design_tasks", {}).get("items", []),
        "production_tasks": progress.get("production_tasks", {}).get("items", []),
        "installation_tasks": progress.get("installation_tasks", {}).get("items", []),
        "acceptances": acceptances,
        "total_paid": progress.get("total_paid", order.get("paid_amount", 0)),
    }


async def _load_quote_snapshot(db, user, business_id: str) -> dict:
    from app.ai_assistant.tools.quote_tools import get_quote_detail

    quote = await get_quote_detail(db, user, business_id)
    if quote.get("error"):
        # 报价转订单后同一条单据的 doc_type 变为 order，按报价查不到。
        # 单据确实存在且已是订单时，改按订单加载快照，而不是报"不存在"。
        from sqlalchemy import select

        from app.models.business_document import BusinessDocument

        doc = (
            await db.execute(
                select(BusinessDocument).where(
                    BusinessDocument.id == _require_uuid(business_id)
                )
            )
        ).scalar_one_or_none()
        if doc is not None and doc.doc_type == "order":
            return await _load_order_snapshot(db, user, business_id)
        raise ValueError(quote["error"])
    return {**quote, "business_type": "quote", "business_id": business_id}


async def _load_task_snapshot(db, user, business_type: str, business_id: str) -> dict:
    from app.services.task_service import (
        DesignTaskService,
        InstallationTaskService,
        ProductionTaskService,
    )

    service_class = {
        "design_task": DesignTaskService,
        "production_task": ProductionTaskService,
        "installation_task": InstallationTaskService,
    }[business_type]
    task = await service_class(db).get_task(_require_uuid(business_id))
    if not task:
        raise ValueError("任务不存在")
    snapshot = {**task, "business_type": business_type, "business_id": business_id}
    terminal_status = {
        "design_task": "confirmed",
        "production_task": "completed",
        "installation_task": "completed",
    }[business_type]
    order_id = str(task.get("order_id") or task.get("document_id") or "")
    if order_id and (
        business_type == "installation_task"
        or task.get("status") == terminal_status
    ):
        order_snapshot = await _load_order_snapshot(db, user, order_id)
        if business_type == "installation_task":
            snapshot["order_installation_address"] = order_snapshot.get(
                "installation_address"
            )
            snapshot["order_delivery_deadline"] = order_snapshot.get(
                "delivery_deadline"
            )
        if task.get("status") == terminal_status:
            snapshot["parent_order_guidance"] = build_workflow_guidance(
                order_snapshot
            )
    return snapshot


async def _load_acceptance_snapshot(db, business_id: str) -> dict:
    from app.services.acceptance_service import AcceptanceService

    acceptance = await AcceptanceService(db).get_detail(_require_uuid(business_id))
    return {
        **acceptance,
        "business_type": "acceptance",
        "business_id": business_id,
    }


async def get_workflow_guidance(db, user, business_type: str, business_id: str):
    """Query current business truth and return deterministic next-step guidance."""
    _require_uuid(business_id)
    if business_type == "order":
        snapshot = await _load_order_snapshot(db, user, business_id)
    elif business_type == "quote":
        snapshot = await _load_quote_snapshot(db, user, business_id)
    elif business_type in ("design_task", "production_task", "installation_task"):
        snapshot = await _load_task_snapshot(db, user, business_type, business_id)
    elif business_type == "acceptance":
        snapshot = await _load_acceptance_snapshot(db, business_id)
    else:
        raise ValueError("暂不支持该业务类型的流程导航")
    return build_workflow_guidance(snapshot)


def register_workflow_tools():
    ToolRegistry().register(
        AiToolDefinition(
            name="get_workflow_guidance",
            description=(
                "查询当前业务记录的真实状态、阻塞条件和下一步操作。"
                "用户问“下一步、怎么操作、做到哪了”时优先调用。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "business_type": {
                        "type": "string",
                        "description": "业务类型",
                        "enum": [
                            "quote",
                            "order",
                            "design_task",
                            "production_task",
                            "installation_task",
                            "acceptance",
                        ],
                    },
                    "business_id": {
                        "type": "string",
                        "description": "当前业务记录ID",
                    },
                },
                "required": ["business_type", "business_id"],
            },
            risk_level="level_1",
            required_permission="customer:read",
            handler=get_workflow_guidance,
        )
    )
