"""Installation preparation checklist and review-only form draft."""

from datetime import datetime

from app.ai_assistant.page_capabilities import build_page_action_semantics

from .task_assignment import has_unassigned_task_items


def _action(label: str, path: str, target_key: str, draft: dict | None = None) -> dict:
    result = {
        "label": label,
        "target_page": "安装任务详情",
        "target_path": path,
        "target_key": target_key,
        "semantics": build_page_action_semantics(target_key, path),
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
    fields = []
    if "order_item_states" not in task:
        # Compatibility for old, hand-built snapshots only. Live task
        # responses use order_item_states and never read the legacy owner.
        fields.append(
            {
                "key": "assigned_to",
                "label": "负责人",
                "value": _text_value(task.get("assigned_to")),
                "source": "task",
                "target_key": "task-item-assignee",
                "pending_detail": "需要在任务处理卡中为订单明细选择执行人",
                "completed_detail": "订单明细已分配执行人",
                "hint": "请在任务处理卡中选择具体订单明细的执行人。",
            }
        )
    elif has_unassigned_task_items(task):
        fields.append(
            {
                "key": "assigned_to",
                "label": "订单明细执行人",
                "value": None,
                "source": "manual",
                "target_key": "task-item-assignee",
                "pending_detail": "仍有订单明细未分配执行人",
                "completed_detail": "订单明细已分配执行人",
                "hint": "请在任务处理卡中勾选明细并改派执行人。",
                "include_in_draft": False,
            }
        )
    else:
        fields.append(
            {
                "key": "assigned_to",
                "label": "订单明细执行人",
                "value": "已分配",
                "source": "task",
                "pending_detail": "订单明细已分配执行人",
                "completed_detail": "订单明细已分配执行人",
                "hint": "订单明细执行人已在任务处理卡中维护。",
                "include_in_draft": False,
            }
        )
    fields.extend([
        {
            "key": "address",
            "label": "安装地址",
            "value": _text_value(task.get("address")),
            "source": "task",
            "suggested_value": _text_value(order_address),
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
    ])

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
        item = {
            "key": field["key"],
            "label": field["label"],
            "state": "pending",
            "detail": field["pending_detail"],
        }
        target_key = field.get("target_key")
        if target_key:
            item["action"] = _action(
                f"处理{field['label']}",
                task_path,
                target_key,
            )
        items.append(item)
        if field.get("include_in_draft", True):
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
