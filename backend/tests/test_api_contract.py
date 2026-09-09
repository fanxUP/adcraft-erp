"""UIX-P04 contract tests for response envelopes, status views and errors."""

import httpx
import pytest

from app.main import app
from app.domain.presentation import make_order_status_view
from app.schemas.common import ActionCapability, StatusView, success_paginated
from app.schemas.outsource import OutsourceTaskResponse
from app.schemas.order import OrderDetailResponse, OrderListResponse
from app.schemas.task import TaskOrderItemOption, TaskQueueItem
from app.services.project_cost_service import ProjectCostService
from app.services.task_service import add_task_contract_fields


def test_status_and_action_contracts_are_typed_and_terminal_aware():
    status = StatusView(code="in_production", label="制作中", tone="info", terminal=False)
    action = ActionCapability(
        allowed=False,
        disabled_reason="外协任务进行中",
        requires_confirmation=False,
    )

    assert status.model_dump() == {
        "code": "in_production",
        "label": "制作中",
        "tone": "info",
        "terminal": False,
    }
    assert action.model_dump() == {
        "allowed": False,
        "disabled_reason": "外协任务进行中",
        "requires_confirmation": False,
    }


def test_order_status_view_is_canonical_and_terminal_aware():
    assert make_order_status_view("in_production").model_dump() == {
        "code": "in_production",
        "label": "制作中",
        "tone": "info",
        "terminal": False,
    }
    assert make_order_status_view("completed").terminal is True


def test_pagination_envelope_has_one_stable_inner_shape():
    payload = success_paginated([{"id": "item-1"}], total=1, page=1, page_size=20)

    assert payload == {
        "code": 0,
        "message": "success",
        "data": {
            "items": [{"id": "item-1"}],
            "total": 1,
            "page": 1,
            "page_size": 20,
        },
    }


def test_task_and_outsource_payloads_expose_canonical_contract_fields():
    assert "status_view" in TaskQueueItem.model_fields
    assert "capabilities" in TaskQueueItem.model_fields
    assert "stage_view" in TaskOrderItemOption.model_fields
    assert "task_status_view" in TaskOrderItemOption.model_fields
    assert "status_view" in OutsourceTaskResponse.model_fields
    assert "status_view" in OrderListResponse.model_fields
    assert "status_view" in OrderDetailResponse.model_fields


def test_task_payload_uses_server_status_semantics_and_object_capability():
    payload = add_task_contract_fields({"status": "completed"}, "installation")

    assert payload["status_view"] == {
        "code": "completed",
        "label": "已完成",
        "tone": "success",
        "terminal": True,
    }
    assert payload["capabilities"]["change_status"] == {
        "allowed": False,
        "disabled_reason": "任务已完成或已取消，不能继续变更状态",
        "requires_confirmation": False,
    }


def test_cost_payload_exposes_scope_state_without_changing_amounts():
    payload = ProjectCostService._add_cost_contract({
        "amount": 1200.5,
        "is_debt": True,
        "is_settled": False,
    })

    assert payload["amount"] == 1200.5
    assert payload["status_view"] == {
        "code": "debt",
        "label": "待结清",
        "tone": "warning",
        "terminal": False,
    }
    assert payload["capabilities"]["settle"]["allowed"] is True


@pytest.mark.asyncio
async def test_validation_error_is_a_contract_envelope_with_request_id():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 42200
    assert body["data"]["fields"]
    assert body["meta"]["request_id"]
    assert response.headers["x-request-id"] == body["meta"]["request_id"]


@pytest.mark.asyncio
async def test_http_error_uses_the_same_envelope_and_preserves_client_request_id():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/task-queue/",
            headers={"X-Request-ID": "contract-401"},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 40100
    assert body["meta"]["request_id"] == "contract-401"
    assert response.headers["x-request-id"] == "contract-401"
