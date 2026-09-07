"""Contract tests for independent task progress fields and queue cards."""

import pytest
from pydantic import ValidationError

from app.schemas.task import (
    DesignTaskUpdate,
    InstallationTaskUpdate,
    ProductionTaskUpdate,
    TaskQueueItem,
)


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
