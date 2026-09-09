"""Contract tests for independent task progress fields and queue cards."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.task import (
    DesignTaskUpdate,
    InstallationTaskUpdate,
    ProductionTaskUpdate,
    TaskQueueItem,
)
from app.services.task_service import _apply_task_item_status_change
from tests.conftest import SAMPLE_ORDER_ITEM_ID, make_mock_design_task


@pytest.mark.parametrize(
    "schema",
    [DesignTaskUpdate, ProductionTaskUpdate, InstallationTaskUpdate],
)
def test_task_progress_accepts_boundary_values(schema):
    assert schema(progress_pct=0).progress_pct == 0
    assert schema(progress_pct=100).progress_pct == 100


@pytest.mark.parametrize(
    "schema",
    [DesignTaskUpdate, ProductionTaskUpdate, InstallationTaskUpdate],
)
@pytest.mark.parametrize("value", [-1, 101])
def test_task_progress_rejects_out_of_range_values(schema, value):
    with pytest.raises(ValidationError):
        schema(progress_pct=value)


def test_task_queue_item_preserves_stage_and_progress():
    item = TaskQueueItem(
        id="task-id",
        task_type="production",
        stage="production",
        task_no="P20260907-0001",
        document_id="order-id",
        project_name="门头制作",
        status="in_progress",
        progress_pct=65,
    )

    assert item.stage == "production"
    assert item.task_type == "production"
    assert item.progress_pct == 65


@pytest.mark.asyncio
async def test_invalid_item_transition_uses_human_readable_status_message():
    """A per-item status error must not expose internal status codes to users."""
    db = AsyncMock()
    task = make_mock_design_task(status="designing", progress_pct=50)

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[SAMPLE_ORDER_ITEM_ID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value={SAMPLE_ORDER_ITEM_ID: ("pending", 0)}),
        ),
    ):
        with pytest.raises(
            ValueError,
            match="所选订单明细当前为“待分配”，不能直接标记为“已完成”，请先推进到“设计中”。",
        ):
            await _apply_task_item_status_change(
                db,
                "design",
                task,
                "confirmed",
                [str(SAMPLE_ORDER_ITEM_ID)],
            )
