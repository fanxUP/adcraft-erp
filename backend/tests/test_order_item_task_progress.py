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
    _validate_order_item_ids,
)
from app.services.task_history_service import task_history_snapshot
from tests.conftest import make_mock_design_task, make_mock_installation_task


ORDER_ID = "33333333-3333-3333-3333-333333333333"
ITEM_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ITEM_UUID = UUID(ITEM_ID)
SECOND_ITEM_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SECOND_ITEM_UUID = UUID(SECOND_ITEM_ID)


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


def test_task_contract_carries_multiple_order_item_identity():
    response = DesignTaskResponse(
        id="task-id",
        design_no="D20260907-0002",
        document_id=ORDER_ID,
        customer_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        project_name="门头项目",
        status="designing",
        order_item_id=ITEM_ID,
        order_item_ids=[ITEM_ID, SECOND_ITEM_ID],
        item_name="前台发光字、侧招字",
        item_names=["前台发光字", "侧招字"],
    )

    assert response.order_item_ids == [ITEM_ID, SECOND_ITEM_ID]
    assert response.item_names == ["前台发光字", "侧招字"]


def test_update_contract_accepts_multiple_order_item_ids():
    from app.schemas.task import DesignTaskUpdate

    update = DesignTaskUpdate(order_item_ids=[ITEM_ID, SECOND_ITEM_ID])

    assert update.order_item_ids == [ITEM_ID, SECOND_ITEM_ID]


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
async def test_order_item_ids_validation_rejects_duplicate_ids():
    db = AsyncMock()

    with pytest.raises(ValueError, match="不能重复"):
        await _validate_order_item_ids(
            db,
            UUID(ORDER_ID),
            [ITEM_ID, ITEM_ID],
        )


def test_many_order_item_link_migration_copies_legacy_links_without_guessing():
    migration = next(
        Path(__file__).parents[1].glob(
            "alembic/versions/p7q8r9s0t1u2_add_task_order_item_many_links.py"
        )
    )
    source = migration.read_text()

    assert 'op.create_table("task_order_item_links"' in source
    assert "task_type" in source
    assert "position" in source
    assert "UNION ALL" in source
    assert "WHERE order_item_id IS NOT NULL" in source


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


@pytest.mark.asyncio
async def test_historical_task_can_be_manually_linked_and_audited():
    db = AsyncMock()
    item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    db.get = AsyncMock(return_value=item)
    task = make_mock_design_task(status="confirmed")
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    async def apply_update(current, data):
        for key, value in data.items():
            setattr(current, key, value)
        return current

    service.repo.update = AsyncMock(side_effect=apply_update)
    service._to_dict = AsyncMock(
        side_effect=lambda value: {
            "order_item_id": str(value.order_item_id),
        }
    )

    with patch("app.services.task_service.record_task_event", new=AsyncMock()):
        result = await service.update_task(task.id, {"order_item_id": ITEM_ID})

    assert task.order_item_id == ITEM_UUID
    assert result["order_item_id"] == ITEM_ID
    assert task_history_snapshot(task)["order_item_id"] == ITEM_ID


@pytest.mark.asyncio
async def test_historical_task_can_be_manually_linked_to_multiple_items():
    db = AsyncMock()
    first_item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    second_item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    db.get = AsyncMock(side_effect=[first_item, second_item])
    task = make_mock_design_task(status="confirmed")
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    async def apply_update(current, data):
        for key, value in data.items():
            setattr(current, key, value)
        return current

    service.repo.update = AsyncMock(side_effect=apply_update)
    service._to_dict = AsyncMock(
        side_effect=lambda value: {
            "order_item_id": str(value.order_item_id),
            "order_item_ids": [ITEM_ID, SECOND_ITEM_ID],
        }
    )

    with patch("app.services.task_service.record_task_event", new=AsyncMock()):
        result = await service.update_task(
            task.id,
            {"order_item_ids": [ITEM_ID, SECOND_ITEM_ID]},
        )

    assert task.order_item_id == ITEM_UUID
    assert result["order_item_ids"] == [ITEM_ID, SECOND_ITEM_ID]
    assert db.execute.await_count >= 2
