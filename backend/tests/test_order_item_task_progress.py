"""第七阶段：订单明细级并行进度契约测试。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.domain.workflows import DESIGN_TASK_WORKFLOW, INSTALLATION_TASK_WORKFLOW
from app.schemas.task import (
    DesignTaskCreate,
    DesignTaskResponse,
    TaskQueueItem,
)
from app.services.task_service import (
    DesignTaskService,
    InstallationTaskService,
    _validate_order_item_id,
)
from tests.conftest import make_mock_design_task, make_mock_installation_task


ORDER_ID = "33333333-3333-3333-3333-333333333333"
ITEM_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ITEM_UUID = UUID(ITEM_ID)


def test_task_contract_carries_order_item_identity():
    create = DesignTaskCreate(order_id=ORDER_ID, order_item_id=ITEM_ID)
    assert create.order_item_id == ITEM_ID

    queue_item = TaskQueueItem(
        id="task-id",
        task_type="design",
        stage="design",
        task_no="D20260907-0001",
        document_id=ORDER_ID,
        order_item_id=ITEM_ID,
        item_name="前台发光字",
        project_name="门头项目",
        status="designing",
        progress_pct=60,
    )
    assert queue_item.order_item_id == ITEM_ID
    assert queue_item.item_name == "前台发光字"


def test_task_responses_expose_nullable_order_item_identity():
    response_fields = DesignTaskResponse.model_fields
    assert "order_item_id" in response_fields
    assert "item_name" in response_fields


def test_new_flow_can_finish_without_extra_review_step():
    assert "confirmed" in DESIGN_TASK_WORKFLOW["designing"]
    assert "completed" in INSTALLATION_TASK_WORKFLOW["in_progress"]


def test_order_item_link_migration_is_additive_and_nullable():
    migration = next(
        Path(__file__).parents[1].glob(
            "alembic/versions/o6p7q8r9s0t1_add_task_order_item_links.py"
        )
    )
    source = migration.read_text()
    assert "op.add_column" in source
    for table in ("design_tasks", "production_tasks", "installation_tasks"):
        assert table in source
        assert "ix_{table}_order_item_id" in source
        assert "fk_{table}_order_item_id" in source
    assert "nullable=True" in source
    assert "UPDATE " not in source


@pytest.mark.asyncio
async def test_order_item_validation_rejects_an_item_from_another_order():
    db = AsyncMock()
    item = MagicMock(document_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
    item.lifecycle_status = "active"
    db.get = AsyncMock(return_value=item)

    with pytest.raises(ValueError, match="不属于当前订单"):
        await _validate_order_item_id(db, UUID(ORDER_ID), ITEM_ID)


@pytest.mark.asyncio
async def test_item_scoped_design_can_finish_without_review_step():
    db = AsyncMock()
    task = make_mock_design_task(status="designing")
    task.order_item_id = ITEM_UUID
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)
    service._to_dict = AsyncMock(side_effect=lambda value: {"status": value.status})

    with (
        patch("app.services.task_service.ensure_task_not_blocked", new=AsyncMock()),
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch("app.services.task_service._item_stage_tasks_completed", new=AsyncMock(return_value=False)),
        patch("app.services.task_service._maybe_complete_order", new=AsyncMock()),
    ):
        result = await service.change_status(task.id, "confirmed")

    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_item_scoped_installation_can_finish_without_acceptance_step():
    db = AsyncMock()
    task = make_mock_installation_task(status="in_progress")
    task.order_item_id = ITEM_UUID
    service = InstallationTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)
    service._to_dict = AsyncMock(side_effect=lambda value: {"status": value.status})

    with (
        patch("app.services.task_service.ensure_task_not_blocked", new=AsyncMock()),
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch("app.services.task_service._maybe_complete_order", new=AsyncMock()),
    ):
        result = await service.change_status(task.id, "completed")

    assert result["status"] == "completed"
