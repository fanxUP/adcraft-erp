"""Guidance rules for quotes, orders and acceptance forms."""

from app.domain.workflows import (
    ACCEPTANCE_WORKFLOW,
    ORDER_WORKFLOW,
    QUOTE_WORKFLOW,
)

from .common import action, guidance_result, unknown_guidance
from .order_progress import attach_order_overview
from .tasks import build_order_task_guidance


def _first_unfinished(tasks: list[dict], terminal_status: str) -> dict | None:
    return next((task for task in tasks if task.get("status") != terminal_status), None)


def build_order_guidance(snapshot: dict) -> dict:
    order_id = str(snapshot.get("business_id") or "")
    status = str(snapshot.get("status") or "")
    order_path = f"/orders/{order_id}"
    stage_labels = {
        "pending_confirm": "订单确认阶段",
        "confirmed": "设计准备阶段",
        "designing": "设计阶段",
        "in_production": "生产阶段",
        "in_installation": "安装阶段",
        "pending_acceptance": "验收阶段",
        "completed": "收款阶段",
        "cancelled": "订单已取消",
    }
    if status not in stage_labels:
        return unknown_guidance(snapshot, "/orders")
    if status == "pending_confirm":
        return guidance_result(
            snapshot,
            stage_labels[status],
            [],
            action(
                "核对并确认订单",
                "订单详情",
                order_path,
                target_status="confirmed",
                target_key="order-status-confirmed",
            ),
            "订单状态变为“已确认”",
            ORDER_WORKFLOW,
        )
    if status == "confirmed":
        tasks = snapshot.get("design_tasks") or []
        if not tasks:
            return guidance_result(
                snapshot,
                stage_labels[status],
                ["尚未创建设计任务"],
                action(
                    "创建并分配设计任务",
                    "订单详情",
                    order_path,
                    target_key="order-create-design",
                ),
                "订单下出现设计任务",
                ORDER_WORKFLOW,
            )
        return guidance_result(
            snapshot,
            stage_labels[status],
            [],
            action(
                "进入设计阶段",
                "订单详情",
                order_path,
                target_status="designing",
                target_key="order-status-designing",
            ),
            "订单状态变为“设计中”",
            ORDER_WORKFLOW,
        )

    task_stages = {
        "designing": ("design_tasks", "design_task", "confirmed", "设计"),
        "in_production": ("production_tasks", "production_task", "completed", "制作"),
        "in_installation": ("installation_tasks", "installation_task", "completed", "安装"),
    }
    if status in task_stages:
        key, task_type, terminal, label = task_stages[status]
        tasks = snapshot.get(key) or []
        if not tasks:
            return guidance_result(
                snapshot,
                stage_labels[status],
                [f"尚未创建{label}任务"],
                action(
                    f"创建并分配{label}任务",
                    "订单详情",
                    order_path,
                    target_key=f"order-create-{task_type.removesuffix('_task')}",
                ),
                f"订单下出现{label}任务",
                ORDER_WORKFLOW,
            )
        unfinished = _first_unfinished(tasks, terminal)
        if unfinished:
            return build_order_task_guidance(snapshot, task_type, unfinished)
        transitions = {
            "designing": ("进入生产阶段", "in_production", "订单状态变为“生产中”并生成制作任务"),
            "in_production": ("进入安装阶段", "in_installation", "订单状态变为“安装中”并生成安装任务"),
            "in_installation": ("提交订单验收", "pending_acceptance", "订单状态变为“待验收”并生成验收单"),
        }
        next_label, target, completion = transitions[status]
        return guidance_result(
            snapshot,
            stage_labels[status],
            [],
            action(
                next_label,
                "订单详情",
                order_path,
                target_status=target,
                target_key=f"order-status-{target}",
            ),
            completion,
            ORDER_WORKFLOW,
        )

    if status == "pending_acceptance":
        acceptances = snapshot.get("acceptances") or []
        if not acceptances:
            return guidance_result(
                snapshot,
                stage_labels[status],
                ["未找到系统自动生成的验收单，请核实订单数据"],
                action("查看验收单列表", "验收管理", "/acceptances"),
                "订单关联到一张验收单",
                ORDER_WORKFLOW,
            )
        acceptance = acceptances[0]
        guidance = build_acceptance_guidance(
            {
                **acceptance,
                "business_type": "acceptance",
                "business_id": str(acceptance.get("id") or ""),
            }
        )
        guidance.update(
            business_type="order",
            business_id=order_id,
            current_status=status,
        )
        return attach_order_overview(guidance, snapshot)

    if status == "completed":
        total = float(snapshot.get("total_amount") or 0)
        paid = float(snapshot.get("total_paid") or 0)
        unpaid = max(0.0, total - paid)
        if unpaid > 0:
            receivable_path = f"/receivables?order_id={order_id}"
            return guidance_result(
                snapshot,
                stage_labels[status],
                [f"订单尚有 {unpaid:.2f} 元未收"],
                action(
                    "跟进并登记收款",
                    "应收管理",
                    receivable_path,
                    target_key="receivable-register-payment",
                ),
                "订单未收金额变为 0.00 元",
                ORDER_WORKFLOW,
            )
        return guidance_result(snapshot, "流程已完成", [], None, "订单已完工且款项已结清", ORDER_WORKFLOW)
    return guidance_result(snapshot, stage_labels[status], [], None, "订单保持已取消状态", ORDER_WORKFLOW)


def build_acceptance_guidance(snapshot: dict) -> dict:
    acceptance_id = str(snapshot.get("business_id") or "")
    status = str(snapshot.get("status") or "")
    path = f"/acceptances/{acceptance_id}"
    if status == "draft":
        blockers = [] if snapshot.get("items") else ["验收单尚无验收明细"]
        return guidance_result(
            snapshot,
            "验收阶段",
            blockers,
            action(
                "完善并提交验收单",
                "验收单详情",
                path,
                target_status="pending",
                target_key="acceptance-status-pending",
            ),
            "验收单状态变为“待验收”",
            ACCEPTANCE_WORKFLOW,
        )
    if status == "pending":
        unfinished = [
            item
            for item in snapshot.get("items") or []
            if item.get("item_status") not in ("accepted", "conditional")
        ]
        blockers = [f"仍有 {len(unfinished)} 项验收明细未确认"] if unfinished else []
        next_action = action(
            "逐项确认验收结果" if unfinished else "确认验收通过",
            "验收单详情",
            path,
            target_status=None if unfinished else "accepted",
            target_key="acceptance-items" if unfinished else "acceptance-status-accepted",
        )
        return guidance_result(
            snapshot,
            "验收阶段",
            blockers,
            next_action,
            "验收单状态变为“已通过”，订单自动完成",
            ACCEPTANCE_WORKFLOW,
        )
    if status == "rejected":
        return guidance_result(
            snapshot,
            "验收整改阶段",
            ["验收已驳回，需要完成整改"],
            action(
                "查看原因并重新整理验收单",
                "验收单详情",
                path,
                target_status="draft",
                target_key="acceptance-status-draft",
            ),
            "验收单恢复为草稿，可重新提交",
            ACCEPTANCE_WORKFLOW,
        )
    if status == "accepted":
        return guidance_result(snapshot, "验收已完成", [], None, "订单已自动变为“已完成”", ACCEPTANCE_WORKFLOW)
    return unknown_guidance(snapshot, "/acceptances")


def build_quote_guidance(snapshot: dict) -> dict:
    quote_id = str(snapshot.get("business_id") or "")
    status = str(snapshot.get("status") or "")
    path = f"/quotes/{quote_id}/edit"
    steps = {
        "draft": ("报价阶段", "核对并确认报价", "confirmed", "报价单状态变为“已确认”"),
        "confirmed": ("报价转单阶段", "转换为正式订单", "converted", "报价单状态变为“已转换”并生成订单"),
    }
    if status in steps:
        step, label, target, completion = steps[status]
        return guidance_result(
            snapshot,
            step,
            [],
            action(
                label,
                "报价编辑",
                path,
                target_status=target,
                target_key=f"quote-status-{target}",
            ),
            completion,
            QUOTE_WORKFLOW,
        )
    if status == "converted":
        return guidance_result(
            snapshot,
            "报价已转订单",
            [],
            action("查看正式订单", "订单管理", "/orders"),
            "在订单管理中继续交付流程",
            QUOTE_WORKFLOW,
        )
    if status == "cancelled":
        return guidance_result(snapshot, "报价已取消", [], None, "报价单保持已取消状态", QUOTE_WORKFLOW)
    return unknown_guidance(snapshot, "/quotes")
