"""Installation preparation checklist and review-only form draft."""

from datetime import datetime


def _action(label: str, path: str, target_key: str, draft: dict | None = None) -> dict:
    result = {
        "label": label,
        "target_page": "安装任务详情",
        "target_path": path,
        "target_key": target_key,
    }
    if draft:
        result["draft"] = draft
    return result


def _text_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def build_installation_preparation(
    task: dict,
    task_path: str,
    *,
    order_address=None,
    order_deadline=None,
) -> dict:
    """Build a deterministic checklist without changing business data."""
    fields = [
        {
            "key": "assigned_to",
            "label": "负责人",
            "value": _text_value(task.get("assigned_to")),
            "source": "task",
            "target_key": "task-assignee",
            "pending_detail": "需要从系统人员中选择安装负责人",
            "completed_detail": "已分配安装负责人",
            "hint": "请选择实际负责本次安装的人员。",
        },
        {
            "key": "address",
            "label": "安装地址",
            "value": _text_value(task.get("address")),
            "source": "task",
            "suggested_value": _text_value(order_address),
            "target_key": "installation-address",
            "pending_detail": (
                "可引用订单安装地址，应用后仍需现场确认"
                if _text_value(order_address)
                else "订单也未提供地址，需要手动填写"
            ),
            "completed_detail": "已填写安装地址",
            "hint": (
                "来自订单安装地址，请核对门牌、楼层和进场位置。"
                if _text_value(order_address)
                else "请填写可直接用于导航和进场的准确地址。"
            ),
        },
        {
            "key": "scheduled_at",
            "label": "计划安装时间",
            "value": _text_value(task.get("scheduled_at")),
            "source": "task",
            "suggested_value": _text_value(order_deadline),
            "target_key": "installation-schedule",
            "pending_detail": (
                "可将订单交付期限作为时间草稿，应用后需确认实际进场时间"
                if _text_value(order_deadline)
                else "订单未提供交付期限，需要手动安排"
            ),
            "completed_detail": "已安排计划安装时间",
            "hint": (
                "参考订单交付期限生成，请改为与客户确认后的实际进场时间。"
                if _text_value(order_deadline)
                else "请与客户和施工人员确认后选择实际进场时间。"
            ),
        },
    ]

    items = []
    draft_fields = []
    completed = 0
    for field in fields:
        if field["value"]:
            completed += 1
            items.append(
                {
                    "key": field["key"],
                    "label": field["label"],
                    "state": "completed",
                    "detail": field["completed_detail"],
                }
            )
            continue

        suggested_value = field.get("suggested_value")
        items.append(
            {
                "key": field["key"],
                "label": field["label"],
                "state": "pending",
                "detail": field["pending_detail"],
                "action": _action(
                    f"处理{field['label']}",
                    task_path,
                    field["target_key"],
                ),
            }
        )
        draft_fields.append(
            {
                "key": field["key"],
                "label": field["label"],
                "value": suggested_value,
                "source": "order" if suggested_value else "manual",
                "hint": field["hint"],
            }
        )

    checklist = {
        "title": "安装准备清单",
        "completed_items": completed,
        "total_items": len(items),
        "items": items,
    }
    if draft_fields:
        checklist["draft_action"] = _action(
            "预览安装准备草稿",
            task_path,
            "installation-draft",
            {
                "kind": "installation_task_update",
                "title": "安装准备信息草稿",
                "fields": draft_fields,
            },
        )
    return checklist
