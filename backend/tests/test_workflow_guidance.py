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
    assert guidance["next_action"]["target_path"] == "/receivables"
    assert guidance["completion_signal"] == "订单未收金额变为 0.00 元"


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
