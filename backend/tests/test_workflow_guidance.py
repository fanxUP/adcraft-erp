from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai_assistant.workflow_guidance import build_workflow_guidance
from app.ai_assistant.service import AiAssistantService
from app.ai_assistant.tools.workflow_tools import (
    get_workflow_guidance,
    register_workflow_tools,
)
from app.ai_assistant.tool_registry import ToolRegistry
from tests.conftest import SAMPLE_ORDER_ID


def test_designing_order_guides_user_to_unfinished_design_task():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "design_tasks": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "design_no": "D20260729-0001",
                    "status": "pending_review",
                }
            ],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
        }
    )

    assert guidance["current_step"] == "设计阶段"
    assert guidance["next_action"]["label"] == "确认设计稿"
    assert guidance["next_action"]["target_path"] == (
        "/design-tasks/22222222-2222-2222-2222-222222222222"
    )
    assert guidance["next_action"]["target_key"] == "task-status-confirmed"
    assert "设计任务 D20260729-0001 待审核确认" in guidance["blockers"]
    assert guidance["allowed_next_statuses"] == [
        "in_production",
        "in_installation",
        "cancelled",
    ]


def test_confirmed_design_tasks_unlock_order_production():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "design_tasks": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "design_no": "D20260729-0001",
                    "status": "confirmed",
                }
            ],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
        }
    )

    assert guidance["blockers"] == []
    assert guidance["next_action"]["label"] == "进入生产阶段"
    assert guidance["next_action"]["target_path"] == f"/orders/{SAMPLE_ORDER_ID}"
    assert guidance["next_action"]["target_status"] == "in_production"
    assert guidance["next_action"]["target_key"] == "order-status-in_production"
    assert guidance["completion_signal"] == "订单状态变为“生产中”并生成制作任务"


def test_completed_order_with_balance_guides_user_to_receivables():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "completed",
            "design_tasks": [],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 600,
        }
    )

    assert guidance["current_step"] == "收款阶段"
    assert guidance["blockers"] == ["订单尚有 400.00 元未收"]
    assert guidance["next_action"]["target_path"] == (
        f"/receivables?order_id={SAMPLE_ORDER_ID}"
    )
    assert guidance["next_action"]["target_key"] == "receivable-register-payment"
    assert guidance["alerts"][0]["action"] == guidance["next_action"]
    assert guidance["completion_signal"] == "订单未收金额变为 0.00 元"


def test_order_guidance_includes_full_delivery_progress():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "design_tasks": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "design_no": "D20260729-0001",
                    "status": "confirmed",
                }
            ],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 200,
        }
    )

    assert guidance["progress"]["completed_steps"] == 1
    assert guidance["progress"]["total_steps"] == 6
    assert guidance["progress"]["current_stage_key"] == "design"
    assert [step["state"] for step in guidance["progress"]["steps"]] == [
        "completed",
        "current",
        "pending",
        "pending",
        "pending",
        "pending",
    ]
    assert guidance["progress"]["steps"][1]["detail"] == "1/1 项设计任务已完成"
    assert guidance["progress"]["steps"][5]["detail"] == "已收 200.00 / 应收 1000.00 元"


def test_order_guidance_reports_actionable_delivery_anomalies():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "in_installation",
            "delivery_deadline": "2026-07-28T09:00:00",
            "installation_address": None,
            "design_tasks": [{"status": "confirmed"}],
            "production_tasks": [{"status": "completed"}],
            "installation_tasks": [
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "installation_no": "I20260729-0001",
                    "status": "pending",
                    "assigned_to": None,
                    "address": None,
                    "scheduled_at": None,
                }
            ],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
            "_now": "2026-07-29T09:00:00",
        }
    )

    assert {alert["code"] for alert in guidance["alerts"]} == {
        "delivery_overdue",
        "task_unassigned",
        "installation_address_missing",
        "installation_schedule_missing",
    }
    assert guidance["alerts"][0]["severity"] == "danger"
    alerts_by_code = {
        alert["code"]: alert
        for alert in guidance["alerts"]
    }
    assert alerts_by_code["task_unassigned"]["action"]["target_key"] == (
        "task-assignee"
    )
    assert alerts_by_code["installation_address_missing"]["action"][
        "target_key"
    ] == "installation-address"
    assert alerts_by_code["installation_schedule_missing"]["action"][
        "target_key"
    ] == "installation-schedule"
    assert all(
        alert["action"]["target_path"]
        == "/installation-tasks/44444444-4444-4444-4444-444444444444"
        for alert in (
            alerts_by_code["task_unassigned"],
            alerts_by_code["installation_address_missing"],
            alerts_by_code["installation_schedule_missing"],
        )
    )
    assert guidance["progress"]["current_stage_key"] == "installation"


def test_installation_stage_builds_reviewable_preparation_checklist():
    task_id = "44444444-4444-4444-4444-444444444444"
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "in_installation",
            "installation_address": "上海市静安区测试路 88 号",
            "delivery_deadline": "2026-08-02T14:30:00",
            "design_tasks": [{"status": "confirmed"}],
            "production_tasks": [{"status": "completed"}],
            "installation_tasks": [
                {
                    "id": task_id,
                    "installation_no": "I20260729-0001",
                    "status": "pending",
                    "assigned_to": None,
                    "address": None,
                    "scheduled_at": None,
                }
            ],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
            "_now": "2026-07-29T09:00:00+08:00",
        }
    )

    checklist = guidance["checklist"]
    assert checklist["title"] == "安装准备清单"
    assert checklist["completed_items"] == 0
    assert checklist["total_items"] == 3
    assert [item["key"] for item in checklist["items"]] == [
        "assigned_to",
        "address",
        "scheduled_at",
    ]
    assert all(item["state"] == "pending" for item in checklist["items"])
    assert checklist["draft_action"]["target_key"] == "installation-draft"
    assert checklist["draft_action"]["target_path"] == (
        f"/installation-tasks/{task_id}"
    )
    fields = {
        field["key"]: field
        for field in checklist["draft_action"]["draft"]["fields"]
    }
    assert fields["assigned_to"]["value"] is None
    assert fields["assigned_to"]["source"] == "manual"
    assert fields["address"]["value"] == "上海市静安区测试路 88 号"
    assert fields["address"]["source"] == "order"
    assert fields["scheduled_at"]["value"] == "2026-08-02T14:30:00"
    assert fields["scheduled_at"]["source"] == "order"

    alerts = {
        alert["code"]: alert
        for alert in guidance["alerts"]
    }
    assert alerts["installation_address_missing"]["title"] == (
        "安装任务地址待补充"
    )


def test_installation_task_guidance_supports_manual_only_draft_fields():
    guidance = build_workflow_guidance(
        {
            "business_type": "installation_task",
            "business_id": "44444444-4444-4444-4444-444444444444",
            "status": "pending",
            "assigned_to": None,
            "address": None,
            "scheduled_at": None,
            "order_installation_address": None,
            "order_delivery_deadline": None,
        }
    )

    checklist = guidance["checklist"]
    fields = checklist["draft_action"]["draft"]["fields"]

    assert checklist["completed_items"] == 0
    assert all(field["value"] is None for field in fields)
    assert all(field["source"] == "manual" for field in fields)


def test_missing_design_file_alert_guides_to_upload_control():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "design_tasks": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "design_no": "D20260729-0001",
                    "status": "designing",
                    "assigned_to": "operator",
                    "design_file_url": None,
                }
            ],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
        }
    )

    alert = next(
        alert
        for alert in guidance["alerts"]
        if alert["code"] == "design_file_missing"
    )
    assert {
        key: alert["action"][key]
        for key in ("label", "target_page", "target_path", "target_key")
    } == {
        "label": "上传或填写设计稿",
        "target_page": "设计任务详情",
        "target_path": "/design-tasks/22222222-2222-2222-2222-222222222222",
        "target_key": "design-file",
    }
    assert alert["action"]["semantics"]["required_permission"] == "design_task:update"


def test_fully_paid_completed_order_marks_every_stage_complete():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "completed",
            "design_tasks": [],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 1000,
        }
    )

    assert guidance["progress"]["completed_steps"] == 6
    assert guidance["progress"]["percent"] == 100
    assert all(
        step["state"] == "completed"
        for step in guidance["progress"]["steps"]
    )
    assert all(
        "尚未创建" not in step["detail"]
        for step in guidance["progress"]["steps"]
    )
    assert guidance["alerts"] == []


def test_delivery_deadline_uses_local_business_timezone():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "pending_confirm",
            "delivery_deadline": "2026-07-29T08:00:00",
            "design_tasks": [],
            "production_tasks": [],
            "installation_tasks": [],
            "acceptances": [],
            "total_amount": 1000,
            "total_paid": 0,
            "_now": "2026-07-29T01:00:00+00:00",
        }
    )

    assert guidance["alerts"][0]["code"] == "delivery_overdue"
    assert "2026-07-29 08:00" in guidance["alerts"][0]["detail"]


def test_pending_acceptance_guides_user_to_confirm_each_item():
    guidance = build_workflow_guidance(
        {
            "business_type": "acceptance",
            "business_id": "55555555-5555-5555-5555-555555555555",
            "status": "pending",
            "items": [
                {"item_status": "accepted"},
                {"item_status": "pending"},
            ],
        }
    )

    assert guidance["current_step"] == "验收阶段"
    assert guidance["blockers"] == ["仍有 1 项验收明细未确认"]
    assert guidance["next_action"]["label"] == "逐项确认验收结果"
    assert guidance["next_action"]["target_path"] == (
        "/acceptances/55555555-5555-5555-5555-555555555555"
    )
    assert guidance["next_action"]["target_key"] == "acceptance-items"


def test_quote_guidance_identifies_the_exact_workflow_control():
    guidance = build_workflow_guidance(
        {
            "business_type": "quote",
            "business_id": "11111111-1111-1111-1111-111111111111",
            "status": "confirmed",
        }
    )

    assert guidance["next_action"]["target_key"] == "quote-status-converted"


@pytest.mark.parametrize(
    ("business_type", "status", "target_key"),
    [
        ("design_task", "designing", "task-status-pending_review"),
        ("production_task", "qc_check", "task-status-completed"),
        ("installation_task", "assigned", "task-status-in_progress"),
    ],
)
def test_task_guidance_identifies_the_target_status_control(
    business_type,
    status,
    target_key,
):
    guidance = build_workflow_guidance(
        {
            "business_type": business_type,
            "business_id": "22222222-2222-2222-2222-222222222222",
            "status": status,
            "assigned_to": "operator",
            "design_file_url": "design.png",
            "address": "测试地址",
            "scheduled_at": "2026-07-29T09:00:00",
        }
    )

    assert guidance["next_action"]["target_key"] == target_key


@pytest.mark.parametrize(
    ("business_type", "terminal_status", "next_label", "next_target_key"),
    [
        ("design_task", "confirmed", "进入生产阶段", "order-status-in_production"),
        ("production_task", "completed", "进入安装阶段", "order-status-in_installation"),
        (
            "installation_task",
            "completed",
            "提交订单验收",
            "order-status-pending_acceptance",
        ),
    ],
)
def test_completed_task_continues_with_parent_order_guidance(
    business_type,
    terminal_status,
    next_label,
    next_target_key,
):
    guidance = build_workflow_guidance(
        {
            "business_type": business_type,
            "business_id": "22222222-2222-2222-2222-222222222222",
            "status": terminal_status,
            "parent_order_guidance": {
                "blockers": [],
                "next_action": {
                    "label": next_label,
                    "target_page": "订单详情",
                    "target_path": f"/orders/{SAMPLE_ORDER_ID}",
                    "target_key": next_target_key,
                },
                "completion_signal": f"完成父订单操作：{next_label}",
            },
        }
    )

    assert guidance["next_action"]["label"] == next_label
    assert guidance["next_action"]["target_path"] == f"/orders/{SAMPLE_ORDER_ID}"
    assert guidance["next_action"]["target_key"] == next_target_key
    assert guidance["completion_signal"] == f"完成父订单操作：{next_label}"


def test_unknown_business_status_returns_safe_guidance():
    guidance = build_workflow_guidance(
        {
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
            "status": "legacy_status",
        }
    )

    assert guidance["current_step"] == "状态待核实"
    assert guidance["next_action"]["label"] == "查看业务详情"
    assert guidance["blockers"] == ["当前状态不在系统标准流程中，请先核实数据"]


@pytest.mark.asyncio
async def test_order_guidance_tool_uses_latest_business_data():
    progress = {
        "order": {
            "id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "total_amount": 1000,
        },
        "design_tasks": {
            "items": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "design_no": "D20260729-0001",
                    "status": "confirmed",
                }
            ]
        },
        "production_tasks": {"items": []},
        "installation_tasks": {"items": []},
        "total_paid": 0,
    }

    with patch(
        "app.ai_assistant.tools.order_tools.get_order_progress",
        new=AsyncMock(return_value=progress),
    ):
        result = await get_workflow_guidance(
            db=MagicMock(),
            user=MagicMock(),
            business_type="order",
            business_id=str(SAMPLE_ORDER_ID),
        )

    assert result["current_status"] == "designing"
    assert result["next_action"]["target_status"] == "in_production"


@pytest.mark.asyncio
async def test_completed_task_guidance_loads_parent_order_progress():
    task_id = "22222222-2222-2222-2222-222222222222"
    task_service = MagicMock()
    task_service.get_task = AsyncMock(
        return_value={
            "id": task_id,
            "status": "confirmed",
            "order_id": str(SAMPLE_ORDER_ID),
        }
    )
    progress = {
        "order": {
            "id": str(SAMPLE_ORDER_ID),
            "status": "designing",
            "total_amount": 1000,
        },
        "design_tasks": {
            "items": [
                {
                    "id": task_id,
                    "design_no": "D20260729-0001",
                    "status": "confirmed",
                }
            ]
        },
        "production_tasks": {"items": []},
        "installation_tasks": {"items": []},
        "total_paid": 0,
    }

    with (
        patch(
            "app.services.task_service.DesignTaskService",
            return_value=task_service,
        ),
        patch(
            "app.ai_assistant.tools.order_tools.get_order_progress",
            new=AsyncMock(return_value=progress),
        ),
    ):
        result = await get_workflow_guidance(
            db=MagicMock(),
            user=MagicMock(),
            business_type="design_task",
            business_id=task_id,
        )

    assert result["next_action"]["label"] == "进入生产阶段"
    assert result["next_action"]["target_path"] == f"/orders/{SAMPLE_ORDER_ID}"


@pytest.mark.asyncio
async def test_installation_task_guidance_loads_order_values_for_draft():
    task_id = "44444444-4444-4444-4444-444444444444"
    task_service = MagicMock()
    task_service.get_task = AsyncMock(
        return_value={
            "id": task_id,
            "status": "pending",
            "order_id": str(SAMPLE_ORDER_ID),
            "assigned_to": None,
            "address": None,
            "scheduled_at": None,
        }
    )
    progress = {
        "order": {
            "id": str(SAMPLE_ORDER_ID),
            "status": "in_installation",
            "installation_address": "上海市静安区测试路 88 号",
            "delivery_deadline": "2026-08-02T14:30:00",
            "total_amount": 1000,
        },
        "design_tasks": {"items": []},
        "production_tasks": {"items": []},
        "installation_tasks": {"items": []},
        "total_paid": 0,
    }

    with (
        patch(
            "app.services.task_service.InstallationTaskService",
            return_value=task_service,
        ),
        patch(
            "app.ai_assistant.tools.order_tools.get_order_progress",
            new=AsyncMock(return_value=progress),
        ),
    ):
        result = await get_workflow_guidance(
            db=MagicMock(),
            user=MagicMock(),
            business_type="installation_task",
            business_id=task_id,
        )

    draft_fields = {
        field["key"]: field
        for field in result["checklist"]["draft_action"]["draft"]["fields"]
    }
    assert draft_fields["address"]["value"] == "上海市静安区测试路 88 号"
    assert draft_fields["scheduled_at"]["value"] == "2026-08-02T14:30:00"


@pytest.mark.asyncio
async def test_pending_acceptance_order_loads_full_acceptance_detail():
    acceptance_id = "55555555-5555-5555-5555-555555555555"
    progress = {
        "order": {
            "id": str(SAMPLE_ORDER_ID),
            "status": "pending_acceptance",
            "total_amount": 1000,
        },
        "design_tasks": {"items": []},
        "production_tasks": {"items": []},
        "installation_tasks": {"items": []},
        "total_paid": 0,
    }
    acceptance_service = MagicMock()
    acceptance_service.list_acceptances = AsyncMock(
        return_value=([{"id": acceptance_id, "status": "pending"}], 1)
    )
    acceptance_service.get_detail = AsyncMock(
        return_value={
            "id": acceptance_id,
            "status": "pending",
            "items": [{"item_status": "pending"}],
        }
    )

    with (
        patch(
            "app.ai_assistant.tools.order_tools.get_order_progress",
            new=AsyncMock(return_value=progress),
        ),
        patch(
            "app.services.acceptance_service.AcceptanceService",
            return_value=acceptance_service,
        ),
    ):
        result = await get_workflow_guidance(
            db=MagicMock(),
            user=MagicMock(),
            business_type="order",
            business_id=str(SAMPLE_ORDER_ID),
        )

    assert result["blockers"] == ["仍有 1 项验收明细未确认"]
    acceptance_service.get_detail.assert_awaited_once()


def test_workflow_guidance_tool_is_registered_as_read_only():
    register_workflow_tools()

    tool = ToolRegistry().get("get_workflow_guidance")

    assert tool is not None
    assert tool.risk_level == "level_1"
    assert tool.requires_confirmation is False


@pytest.mark.asyncio
async def test_direct_guidance_uses_permission_gated_tool_executor():
    service = object.__new__(AiAssistantService)
    service.tool_executor = MagicMock()
    service.tool_executor.execute_tool = AsyncMock(
        return_value={"status": "success", "result": {"current_step": "设计阶段"}}
    )
    user = MagicMock()

    result = await service.get_workflow_guidance(
        user,
        "order",
        SAMPLE_ORDER_ID,
    )

    assert result["status"] == "success"
    service.tool_executor.execute_tool.assert_awaited_once_with(
        tool_name="get_workflow_guidance",
        args={
            "business_type": "order",
            "business_id": str(SAMPLE_ORDER_ID),
        },
        user=user,
    )
