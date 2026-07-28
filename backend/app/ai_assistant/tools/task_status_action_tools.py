"""设计、制作、安装任务的 AI 安全状态推进工具。"""

from functools import partial
from uuid import UUID

from app.ai_assistant.tool_registry import AiToolDefinition, ToolRegistry
from app.domain.workflows import (
    DESIGN_TASK_WORKFLOW,
    INSTALLATION_TASK_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
)


TASK_CONFIGS = {
    "design_task": {
        "label": "设计任务",
        "number_field": "design_no",
        "workflow": DESIGN_TASK_WORKFLOW,
        "permission": "design_task:change_status",
        "tool_name": "change_design_task_status",
        "status_labels": {
            "pending": "待分配",
            "designing": "设计中",
            "pending_review": "待审核",
            "revision": "待修改",
            "confirmed": "已确认",
        },
    },
    "production_task": {
        "label": "制作任务",
        "number_field": "production_no",
        "workflow": PRODUCTION_TASK_WORKFLOW,
        "permission": "production_task:change_status",
        "tool_name": "change_production_task_status",
        "status_labels": {
            "pending": "待制作",
            "queued": "排队中",
            "in_progress": "制作中",
            "qc_check": "待质检",
            "rework": "返工",
            "completed": "已完成",
        },
    },
    "installation_task": {
        "label": "安装任务",
        "number_field": "installation_no",
        "workflow": INSTALLATION_TASK_WORKFLOW,
        "permission": "installation_task:change_status",
        "tool_name": "change_installation_task_status",
        "status_labels": {
            "pending": "待分配",
            "assigned": "已分配",
            "in_progress": "安装中",
            "pending_acceptance": "待验收",
            "completed": "已完成",
        },
    },
}


def _get_task_service(db, task_type: str):
    from app.services.task_service import (
        DesignTaskService,
        InstallationTaskService,
        ProductionTaskService,
    )

    services = {
        "design_task": DesignTaskService,
        "production_task": ProductionTaskService,
        "installation_task": InstallationTaskService,
    }
    return services[task_type](db)


def _validate_task_requirements(task_type: str, task: dict, target_status: str) -> None:
    current_status = str(task.get("status") or "")
    if current_status == "pending" and not task.get("assigned_to"):
        raise ValueError("任务尚未分配负责人，请先完成分配")

    if (
        task_type == "design_task"
        and target_status == "pending_review"
        and not task.get("design_file_url")
    ):
        raise ValueError("尚未上传设计稿，不能提交审核")

    if task_type == "installation_task" and target_status in {
        "assigned",
        "in_progress",
    }:
        if not task.get("address"):
            raise ValueError("尚未填写安装地址")
        if not task.get("scheduled_at"):
            raise ValueError("尚未安排安装时间")


def _validate_transition(
    task_type: str,
    task: dict,
    current_status: str,
    target_status: str,
    *,
    stale_message: str,
) -> None:
    config = TASK_CONFIGS[task_type]
    live_status = str(task.get("status") or "")
    labels = config["status_labels"]
    if live_status != current_status:
        raise ValueError(
            f"{config['label']}状态已变化，当前为"
            f"「{labels.get(live_status, live_status)}」，{stale_message}",
        )
    if target_status not in allowed_targets(config["workflow"], live_status):
        raise ValueError(f"不允许从 {live_status} 流转到 {target_status}")
    _validate_task_requirements(task_type, task, target_status)


async def preview_task_status_change(
    db,
    user,
    *,
    task_type: str,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    config = TASK_CONFIGS[task_type]
    service = _get_task_service(db, task_type)
    task = await service.get_task(UUID(business_id))
    if not task:
        raise ValueError(f"{config['label']}不存在")
    _validate_transition(
        task_type,
        task,
        current_status,
        target_status,
        stale_message="请重新获取流程建议",
    )
    labels = config["status_labels"]
    return {
        "action_label": f"推进{config['label']}状态",
        "business_type": task_type,
        "business_id": business_id,
        "business_no": task.get(config["number_field"], ""),
        "project_name": task.get("project_name", ""),
        "current_status": current_status,
        "current_status_label": labels.get(current_status, current_status),
        "target_status": target_status,
        "target_status_label": labels.get(target_status, target_status),
        "reason": reason,
        "effects": [
            f"{config['label']}将进入「{labels.get(target_status, target_status)}」",
        ],
        "note": "确认后才会执行；执行前系统会再次核验任务状态、前置条件和权限。",
    }


async def execute_task_status_change(
    db,
    user,
    *,
    task_type: str,
    business_id: str,
    current_status: str,
    target_status: str,
    reason: str = "",
):
    config = TASK_CONFIGS[task_type]
    service = _get_task_service(db, task_type)
    task = await service.get_task(UUID(business_id))
    if not task:
        raise ValueError(f"{config['label']}不存在")
    _validate_transition(
        task_type,
        task,
        current_status,
        target_status,
        stale_message="原操作已停止",
    )
    updated = await service.change_status(
        UUID(business_id),
        target_status,
        user.id,
    )
    labels = config["status_labels"]
    return {
        "status": "updated",
        "business_type": task_type,
        "business_id": business_id,
        "business_no": updated.get(config["number_field"], ""),
        "previous_status": current_status,
        "current_status": updated.get("status", target_status),
        "reason": reason,
        "message": (
            f"{config['label']}状态已从「{labels.get(current_status, current_status)}」"
            f"推进到「{labels.get(target_status, target_status)}」"
        ),
    }


def register_task_status_action_tools():
    registry = ToolRegistry()
    for task_type, config in TASK_CONFIGS.items():
        workflow = config["workflow"]
        registry.register(AiToolDefinition(
            name=config["tool_name"],
            description=(
                f"根据流程导航推进{config['label']}状态。系统先展示影响预览，"
                "用户确认后才执行，并在执行前重新核验实时状态和前置条件。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "business_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": f"{config['label']}ID",
                    },
                    "current_status": {
                        "type": "string",
                        "enum": list(workflow),
                        "description": "流程导航核验出的当前状态",
                    },
                    "target_status": {
                        "type": "string",
                        "enum": list(workflow),
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
            required_permission=config["permission"],
            requires_confirmation=True,
            preview_handler=partial(
                preview_task_status_change,
                task_type=task_type,
            ),
            handler=partial(
                execute_task_status_change,
                task_type=task_type,
            ),
        ))
