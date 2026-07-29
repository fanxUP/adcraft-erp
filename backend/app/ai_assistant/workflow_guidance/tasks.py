"""Guidance rules for design, production and installation tasks."""

from app.domain.workflows import (
    DESIGN_TASK_WORKFLOW,
    INSTALLATION_TASK_WORKFLOW,
    ORDER_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
)

from .common import action, guidance_result, unknown_guidance
from .order_progress import attach_order_overview


TASK_CONFIGS = {
    "design_task": {
        "label": "设计任务",
        "step": "设计阶段",
        "page": "设计任务详情",
        "prefix": "/design-tasks",
        "workflow": DESIGN_TASK_WORKFLOW,
        "actions": {
            "pending": ("分配并开始设计", "designing", "设计任务状态变为“设计中”"),
            "designing": ("上传设计稿并提交审核", "pending_review", "设计任务状态变为“待审核”"),
            "pending_review": ("确认设计稿", "confirmed", "设计任务状态变为“已确认”"),
            "revision": ("按反馈修改设计稿", "designing", "设计任务重新进入“设计中”"),
        },
        "terminal": "confirmed",
    },
    "production_task": {
        "label": "制作任务",
        "step": "生产阶段",
        "page": "制作任务详情",
        "prefix": "/production-tasks",
        "workflow": PRODUCTION_TASK_WORKFLOW,
        "actions": {
            "pending": ("排产并开始制作", "in_progress", "制作任务状态变为“生产中”"),
            "queued": ("开始制作", "in_progress", "制作任务状态变为“生产中”"),
            "in_progress": ("完成制作并提交质检", "qc_check", "制作任务状态变为“质检中”"),
            "qc_check": ("确认质检完成", "completed", "制作任务状态变为“已完成”"),
            "rework": ("完成返工并重新质检", "qc_check", "制作任务重新进入“质检中”"),
        },
        "terminal": "completed",
    },
    "installation_task": {
        "label": "安装任务",
        "step": "安装阶段",
        "page": "安装任务详情",
        "prefix": "/installation-tasks",
        "workflow": INSTALLATION_TASK_WORKFLOW,
        "actions": {
            "pending": ("分配安装人员", "assigned", "安装任务状态变为“已分配”"),
            "assigned": ("开始现场安装", "in_progress", "安装任务状态变为“安装中”"),
            "in_progress": ("提交安装完成", "pending_acceptance", "安装任务状态变为“待验收”"),
            "pending_acceptance": ("确认安装任务完成", "completed", "安装任务状态变为“已完成”"),
        },
        "terminal": "completed",
    },
}


def build_task_guidance(snapshot: dict, task_type: str) -> dict:
    config = TASK_CONFIGS[task_type]
    task_id = str(snapshot.get("business_id") or "")
    status = str(snapshot.get("status") or "")
    if status == config["terminal"]:
        parent_guidance = snapshot.get("parent_order_guidance") or {}
        next_action = parent_guidance.get("next_action")
        return guidance_result(
            snapshot,
            f"{config['label']}已完成",
            list(parent_guidance.get("blockers") or []),
            next_action,
            (
                str(parent_guidance.get("completion_signal"))
                if next_action
                else f"{config['page']}已完成，父订单暂无待处理步骤"
            ),
            config["workflow"],
        )

    next_step = config["actions"].get(status)
    if not next_step:
        return unknown_guidance(snapshot, config["prefix"])

    blockers = []
    if status == "pending" and not snapshot.get("assigned_to"):
        blockers.append("尚未分配负责人")
    if task_type == "design_task" and status == "designing" and not snapshot.get("design_file_url"):
        blockers.append("尚未上传设计稿")
    if task_type == "installation_task" and status in ("pending", "assigned"):
        if not snapshot.get("address"):
            blockers.append("尚未填写安装地址")
        if not snapshot.get("scheduled_at"):
            blockers.append("尚未安排安装时间")

    label, target_status, completion = next_step
    return guidance_result(
        snapshot,
        config["step"],
        blockers,
        action(
            label,
            config["page"],
            f"{config['prefix']}/{task_id}",
            target_status=target_status,
            target_key=f"task-status-{target_status}",
        ),
        completion,
        config["workflow"],
    )


def build_order_task_guidance(
    order_snapshot: dict,
    task_type: str,
    task: dict,
) -> dict:
    guidance = build_task_guidance(
        {
            **task,
            "business_type": task_type,
            "business_id": str(task.get("id") or ""),
        },
        task_type,
    )
    config = TASK_CONFIGS[task_type]
    task_no = (
        task.get("design_no")
        or task.get("production_no")
        or task.get("installation_no")
        or "未编号"
    )
    status_messages = {
        "pending_review": "待审核确认",
        "revision": "待修改",
        "qc_check": "待质检确认",
        "rework": "待返工",
        "pending_acceptance": "待确认完成",
    }
    message = status_messages.get(str(task.get("status")), "尚未完成")
    guidance.update(
        business_type="order",
        business_id=order_snapshot.get("business_id"),
        current_status=order_snapshot.get("status"),
        blockers=[f"{config['label']} {task_no} {message}"],
        allowed_next_statuses=list(
            allowed_targets(ORDER_WORKFLOW, str(order_snapshot.get("status") or ""))
        ),
    )
    return attach_order_overview(guidance, order_snapshot)
