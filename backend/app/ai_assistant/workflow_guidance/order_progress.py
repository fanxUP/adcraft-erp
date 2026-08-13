"""Deterministic order progress and anomaly aggregation."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.ai_assistant.page_capabilities import build_page_action_semantics

from .installation_preparation import build_installation_preparation


STAGES = (
    ("order", "订单确认"),
    ("design", "设计"),
    ("production", "制作"),
    ("installation", "安装"),
    ("acceptance", "验收"),
    ("payment", "回款"),
)
BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")

CURRENT_STAGE_INDEX = {
    "pending_confirm": 0,
    "confirmed": 1,
    "designing": 1,
    "in_production": 2,
    "in_installation": 3,
    "completed": 4,
    "cancelled": 0,
}


def _money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _task_detail(tasks: list[dict], terminal_status: str, label: str) -> str:
    if not tasks:
        return f"尚未创建{label}任务"
    completed = sum(task.get("status") == terminal_status for task in tasks)
    return f"{completed}/{len(tasks)} 项{label}任务已完成"


def _acceptance_detail(snapshot: dict) -> str:
    status = str(snapshot.get("status") or "")
    if status == "completed":
        return "验收已完成"
    acceptances = snapshot.get("acceptances") or []
    if not acceptances:
        return "尚未进入验收"
    acceptance = acceptances[0]
    if acceptance.get("status") == "accepted":
        return "验收已通过"
    items = acceptance.get("items") or []
    confirmed = sum(
        item.get("item_status") in ("accepted", "conditional")
        for item in items
    )
    return f"{confirmed}/{len(items)} 项验收明细已确认"


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BUSINESS_TIMEZONE).astimezone(timezone.utc)
    return parsed.astimezone(timezone.utc)


def _workflow_action(
    label: str,
    page: str,
    path: str,
    target_key: str,
) -> dict:
    return {
        "label": label,
        "target_page": page,
        "target_path": path,
        "target_key": target_key,
        "semantics": build_page_action_semantics(target_key, path),
    }


def _alert(
    code: str,
    severity: str,
    title: str,
    detail: str,
    action: dict | None = None,
) -> dict:
    result = {
        "code": code,
        "severity": severity,
        "title": title,
        "detail": detail,
    }
    if action:
        result["action"] = action
    return result


def _current_task(snapshot: dict, key: str, terminal_status: str) -> dict | None:
    return next(
        (
            task
            for task in snapshot.get(key) or []
            if task.get("status") != terminal_status
        ),
        None,
    )


def build_order_alerts(
    snapshot: dict,
    next_action: dict | None = None,
) -> list[dict]:
    status = str(snapshot.get("status") or "")
    if status == "cancelled":
        return [
            _alert(
                "order_cancelled",
                "info",
                "订单流程已终止",
                "该订单已取消，不再继续设计、制作、安装与验收。",
            )
        ]

    alerts: list[dict] = []
    now = _parse_datetime(snapshot.get("_now")) or datetime.now(timezone.utc)
    deadline = _parse_datetime(snapshot.get("delivery_deadline"))
    if status not in ("completed", "cancelled") and deadline and deadline < now:
        alerts.append(
            _alert(
                "delivery_overdue",
                "danger",
                "订单已超过交付期限",
                "计划交付时间为 "
                f"{deadline.astimezone(BUSINESS_TIMEZONE).strftime('%Y-%m-%d %H:%M')}"
                "，请立即核实施工进度。",
                next_action,
            )
        )

    task_config = {
        "designing": (
            "design_tasks",
            "confirmed",
            "设计任务",
            "设计任务详情",
            "/design-tasks",
        ),
        "in_production": (
            "production_tasks",
            "completed",
            "制作任务",
            "制作任务详情",
            "/production-tasks",
        ),
        "in_installation": (
            "installation_tasks",
            "completed",
            "安装任务",
            "安装任务详情",
            "/installation-tasks",
        ),
    }
    config = task_config.get(status)
    current_task = None
    task_page = ""
    task_path = ""
    if config:
        key, terminal_status, label, task_page, prefix = config
        current_task = _current_task(snapshot, key, terminal_status)
        task_path = f"{prefix}/{current_task.get('id')}" if current_task else ""
        if current_task and not current_task.get("assigned_to"):
            alerts.append(
                _alert(
                    "task_unassigned",
                    "warning",
                    f"{label}尚未分配负责人",
                    "分配负责人后，AI 才能继续检查责任人与执行进度。",
                    _workflow_action(
                        "分配任务负责人",
                        task_page,
                        task_path,
                        "task-assignee",
                    ),
                )
            )

    if (
        status == "designing"
        and current_task
        and current_task.get("status") == "designing"
        and not current_task.get("design_file_url")
    ):
        alerts.append(
            _alert(
                "design_file_missing",
                "warning",
                "设计稿尚未上传",
                "上传设计稿后才能提交客户或内部审核。",
                _workflow_action(
                    "上传或填写设计稿",
                    task_page,
                    task_path,
                    "design-file",
                ),
            )
        )

    if status == "in_installation" and current_task:
        if not current_task.get("address"):
            has_order_address = bool(snapshot.get("installation_address"))
            alerts.append(
                _alert(
                    "installation_address_missing",
                    "warning",
                    "安装任务地址待补充",
                    (
                        "订单已有安装地址，可生成草稿同步到任务并现场确认。"
                        if has_order_address
                        else "订单和任务均未填写地址，请补充后再安排人员和车辆。"
                    ),
                    _workflow_action(
                        "补充安装地址",
                        task_page,
                        task_path,
                        "installation-address",
                    ),
                )
            )
        if not current_task.get("scheduled_at"):
            alerts.append(
                _alert(
                    "installation_schedule_missing",
                    "warning",
                    "安装时间尚未安排",
                    "设置计划安装时间，便于协调现场与施工人员。",
                    _workflow_action(
                        "安排安装时间",
                        task_page,
                        task_path,
                        "installation-schedule",
                    ),
                )
            )

    total = _money(snapshot.get("total_amount"))
    paid = _money(snapshot.get("total_paid"))
    if status == "completed" and total > paid:
        alerts.append(
            _alert(
                "receivable_outstanding",
                "warning",
                "完工订单仍有应收款",
                f"尚有 {total - paid:.2f} 元未收，请继续跟进回款。",
                next_action,
            )
        )
    return alerts


def build_order_progress(snapshot: dict) -> dict:
    status = str(snapshot.get("status") or "")
    total = _money(snapshot.get("total_amount"))
    paid = _money(snapshot.get("total_paid"))
    paid_in_full = status == "completed" and paid >= total
    current_index = CURRENT_STAGE_INDEX.get(status, 0)
    completed_steps = len(STAGES) if paid_in_full else current_index

    details = (
        "订单已确认" if status != "pending_confirm" else "等待核对并确认订单",
        _task_detail(snapshot.get("design_tasks") or [], "confirmed", "设计"),
        _task_detail(snapshot.get("production_tasks") or [], "completed", "制作"),
        _task_detail(snapshot.get("installation_tasks") or [], "completed", "安装"),
        _acceptance_detail(snapshot),
        f"已收 {paid:.2f} / 应收 {total:.2f} 元",
    )
    steps = []
    for index, ((key, label), detail) in enumerate(zip(STAGES, details)):
        if status == "cancelled" and index == 0:
            state = "blocked"
            detail = "订单已取消，流程终止"
        elif index < completed_steps or paid_in_full:
            state = "completed"
        elif index == current_index:
            state = "current"
        else:
            state = "pending"
        if state == "completed" and detail.startswith("尚未创建"):
            detail = f"{label}阶段已完成"
        steps.append(
            {"key": key, "label": label, "state": state, "detail": detail}
        )

    return {
        "completed_steps": completed_steps,
        "total_steps": len(STAGES),
        "percent": round(completed_steps / len(STAGES) * 100),
        "current_stage_key": STAGES[current_index][0],
        "steps": steps,
    }


def attach_order_overview(result: dict, snapshot: dict) -> dict:
    result["progress"] = build_order_progress(snapshot)
    result["alerts"] = build_order_alerts(snapshot, result.get("next_action"))
    if str(snapshot.get("status") or "") == "in_installation":
        task = _current_task(snapshot, "installation_tasks", "completed")
        if task and task.get("id"):
            result["checklist"] = build_installation_preparation(
                task,
                f"/installation-tasks/{task['id']}",
                order_address=snapshot.get("installation_address"),
                order_deadline=snapshot.get("delivery_deadline"),
            )
    return result
