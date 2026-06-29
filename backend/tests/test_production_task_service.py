"""Tests for ProductionTaskService: status transitions, CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.task_service import ProductionTaskService
from tests.conftest import (
    SAMPLE_TASK_ID,
    SAMPLE_USER_ID,
    make_mock_production_task,
)


@pytest.fixture
def mock_repo():
    """Create a mock ProductionTaskRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.create = AsyncMock()
    repo.list_tasks = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def service(mock_repo):
    """Create ProductionTaskService with a mocked repository."""
    with patch("app.services.task_service.ProductionTaskRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = ProductionTaskService(db)
        svc.repo = mock_repo
        yield svc


# --- Status Transition Tests ---

TRANSITION_TABLE = [
    ("pending", "queued", True),
    ("pending", "in_progress", True),
    ("pending", "qc_check", False),
    ("pending", "completed", False),
    ("queued", "in_progress", True),
    ("queued", "pending", True),
    ("queued", "completed", False),
    ("in_progress", "qc_check", True),
    ("in_progress", "rework", True),
    ("in_progress", "completed", True),
    ("in_progress", "queued", False),
    ("in_progress", "pending", False),
    ("qc_check", "completed", True),
    ("qc_check", "rework", True),
    ("qc_check", "in_progress", False),
    ("rework", "in_progress", True),
    ("rework", "qc_check", True),
    ("rework", "completed", False),
    ("completed", "in_progress", False),
    ("completed", "pending", False),
    ("completed", "queued", False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status,should_succeed", TRANSITION_TABLE)
async def test_status_transitions(service, mock_repo, from_status, to_status, should_succeed):
    """Verify all allowed and forbidden status transitions."""
    task = make_mock_production_task(status=from_status)
    mock_repo.get_by_id.return_value = task

    if should_succeed:
        result = await service.change_status(SAMPLE_TASK_ID, to_status, SAMPLE_USER_ID)
        assert result["status"] == to_status
    else:
        with pytest.raises(ValueError):
            await service.change_status(SAMPLE_TASK_ID, to_status, SAMPLE_USER_ID)


@pytest.mark.asyncio
async def test_completed_sets_timestamp(service, mock_repo):
    """Transitioning to 'completed' sets the completed_at timestamp."""
    task = make_mock_production_task(status="qc_check")
    mock_repo.get_by_id.return_value = task

    result = await service.change_status(SAMPLE_TASK_ID, "completed", SAMPLE_USER_ID)

    assert result["status"] == "completed"
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_change_status_nonexistent_task(service, mock_repo):
    """Changing status on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="制作任务不存在"):
        await service.change_status(SAMPLE_TASK_ID, "in_progress", SAMPLE_USER_ID)


# --- Get Task Tests ---

@pytest.mark.asyncio
async def test_get_task_found(service, mock_repo):
    """get_task returns correct data for an existing task."""
    task = make_mock_production_task()
    mock_repo.get_by_id.return_value = task

    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_TASK_ID)
    assert result["production_no"] == "P20260629-0001"
    assert result["project_name"] == "测试制作任务"
    assert result["status"] == "pending"
    assert result["length"] == 2.5
    assert result["width"] == 1.5
    assert result["height"] == 0.3
    assert result["quantity"] == 10


@pytest.mark.asyncio
async def test_get_task_not_found(service, mock_repo):
    """get_task returns None for a non-existent task."""
    mock_repo.get_by_id.return_value = None
    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is None


# --- To Dict Serialization ---

def test_to_dict_includes_all_fields(service):
    """_to_dict properly serializes a production task object."""
    now = datetime.now(timezone.utc)
    task = make_mock_production_task(
        task_id=SAMPLE_TASK_ID,
        production_no="P20260629-0042",
        status="in_progress",
        material_id=SAMPLE_USER_ID,
        process_id=SAMPLE_TASK_ID,
        length=3.0,
        width=2.0,
        height=0.5,
        quantity=50,
        qc_result="pass",
        rework_reason=None,
        completed_at=None,
    )
    d = service._to_dict(task)
    assert d["id"] == str(SAMPLE_TASK_ID)
    assert d["production_no"] == "P20260629-0042"
    assert d["status"] == "in_progress"
    assert d["material_id"] == str(SAMPLE_USER_ID)
    assert d["process_id"] == str(SAMPLE_TASK_ID)
    assert d["length"] == 3.0
    assert d["width"] == 2.0
    assert d["height"] == 0.5
    assert d["quantity"] == 50
    assert d["qc_result"] == "pass"
    assert d["rework_reason"] is None
    assert d["completed_at"] is None
    assert isinstance(d["attachments"], list)


def test_to_dict_with_dimensions_none(service):
    """_to_dict handles None dimensional fields."""
    task = make_mock_production_task(
        length=None,
        width=None,
        height=None,
        material_id=None,
        process_id=None,
    )
    d = service._to_dict(task)
    assert d["length"] is None
    assert d["width"] is None
    assert d["height"] is None
    assert d["material_id"] is None
    assert d["process_id"] is None


def test_to_dict_with_attachments(service):
    """_to_dict serializes attachment objects."""
    att = MagicMock()
    att.id = "att-1"
    att.related_type = "production_task"
    att.related_id = SAMPLE_TASK_ID
    att.filename = "product.pdf"
    att.file_path = "202606/product.pdf"
    att.file_size = 4096
    att.file_type = "application/pdf"
    att.category = "spec"
    att.uploaded_by = SAMPLE_USER_ID
    att.remark = "规格书"
    att.created_at = datetime.now(timezone.utc)

    task = make_mock_production_task(attachments=[att])
    d = service._to_dict(task)
    assert len(d["attachments"]) == 1
    assert d["attachments"][0]["filename"] == "product.pdf"


# --- List Tasks Tests ---

@pytest.mark.asyncio
async def test_list_tasks_empty(service, mock_repo):
    """list_tasks returns empty list when no tasks exist."""
    mock_repo.list_tasks.return_value = ([], 0)
    tasks, total = await service.list_tasks(page=1, page_size=20)
    assert tasks == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_tasks_with_results(service, mock_repo):
    """list_tasks returns serialized tasks and total count."""
    task1 = make_mock_production_task(task_id=SAMPLE_TASK_ID, project_name="项目A")
    task2 = make_mock_production_task(
        task_id=SAMPLE_USER_ID,
        production_no="P20260629-0002",
        project_name="项目B",
    )
    mock_repo.list_tasks.return_value = ([task1, task2], 2)

    tasks, total = await service.list_tasks(page=1, page_size=20)
    assert total == 2
    assert len(tasks) == 2
    assert tasks[0]["project_name"] == "项目A"
    assert tasks[1]["project_name"] == "项目B"


# --- Create Task Tests ---

@pytest.mark.asyncio
async def test_create_task(service, mock_repo):
    """create_task sets production_no, status, and returns serialized result."""

    async def create_side_effect(data):
        return make_mock_production_task(
            production_no="P20260629-0050",
            project_name=data.get("project_name", "默认"),
            quantity=data.get("quantity", 1),
        )

    mock_repo.create.side_effect = create_side_effect

    with patch("app.services.task_service.generate_production_no", AsyncMock(return_value="P20260629-0050")):
        result = await service.create_task({
            "order_id": SAMPLE_TASK_ID,
            "customer_id": SAMPLE_USER_ID,
            "project_name": "新制作",
            "quantity": 5,
        })

    assert result["production_no"] == "P20260629-0050"
    assert result["project_name"] == "新制作"


# --- Update Task Tests ---

@pytest.mark.asyncio
async def test_update_task(service, mock_repo):
    """update_task modifies and returns updated task."""
    task = make_mock_production_task(project_name="旧名称", quantity=10)
    mock_repo.get_by_id.return_value = task
    updated = make_mock_production_task(project_name="新名称", quantity=20)
    mock_repo.update.return_value = updated

    result = await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称", "quantity": 20})
    assert result["project_name"] == "新名称"


@pytest.mark.asyncio
async def test_update_nonexistent_task(service, mock_repo):
    """update_task on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="制作任务不存在"):
        await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称"})
