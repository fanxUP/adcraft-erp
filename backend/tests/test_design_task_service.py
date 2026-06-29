"""Tests for DesignTaskService: status transitions, CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.task_service import DesignTaskService
from tests.conftest import (
    SAMPLE_TASK_ID,
    SAMPLE_USER_ID,
    make_mock_design_task,
)


@pytest.fixture
def mock_repo():
    """Create a mock DesignTaskRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.create = AsyncMock()
    repo.list_tasks = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def service(mock_repo):
    """Create DesignTaskService with a mocked repository."""
    with patch("app.services.task_service.DesignTaskRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = DesignTaskService(db)
        svc.repo = mock_repo
        yield svc


# --- Status Transition Tests ---

TRANSITION_TABLE = [
    ("pending", "designing", True),
    ("pending", "pending_review", False),
    ("pending", "confirmed", False),
    ("designing", "pending_review", True),
    ("designing", "pending", True),
    ("designing", "confirmed", False),
    ("pending_review", "confirmed", True),
    ("pending_review", "revision", True),
    ("pending_review", "designing", False),
    ("revision", "designing", True),
    ("revision", "pending_review", True),
    ("revision", "confirmed", False),
    ("confirmed", "designing", False),
    ("confirmed", "pending", False),
    ("confirmed", "revision", False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status,should_succeed", TRANSITION_TABLE)
async def test_status_transitions(service, mock_repo, from_status, to_status, should_succeed):
    """Verify all allowed and forbidden status transitions."""
    task = make_mock_design_task(status=from_status)
    mock_repo.get_by_id.return_value = task

    if should_succeed:
        result = await service.change_status(SAMPLE_TASK_ID, to_status, SAMPLE_USER_ID)
        assert result["status"] == to_status
    else:
        with pytest.raises(ValueError):
            await service.change_status(SAMPLE_TASK_ID, to_status, SAMPLE_USER_ID)


@pytest.mark.asyncio
async def test_completed_sets_timestamp(service, mock_repo):
    """Transitioning to 'confirmed' sets the completed_at timestamp."""
    task = make_mock_design_task(status="pending_review")
    mock_repo.get_by_id.return_value = task

    result = await service.change_status(SAMPLE_TASK_ID, "confirmed", SAMPLE_USER_ID)

    assert result["status"] == "confirmed"
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_change_status_nonexistent_task(service, mock_repo):
    """Changing status on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="设计任务不存在"):
        await service.change_status(SAMPLE_TASK_ID, "designing", SAMPLE_USER_ID)


# --- Get Task Tests ---

@pytest.mark.asyncio
async def test_get_task_found(service, mock_repo):
    """get_task returns correct data for an existing task."""
    task = make_mock_design_task()
    mock_repo.get_by_id.return_value = task

    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_TASK_ID)
    assert result["design_no"] == "D20260629-0001"
    assert result["project_name"] == "测试设计任务"
    assert result["status"] == "pending"
    assert result["description"] == "这是一个测试设计任务"
    assert result["design_file_url"] is None
    assert result["client_comments"] is None


@pytest.mark.asyncio
async def test_get_task_not_found(service, mock_repo):
    """get_task returns None for a non-existent task."""
    mock_repo.get_by_id.return_value = None
    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is None


# --- To Dict Serialization ---

def test_to_dict_includes_all_fields(service):
    """_to_dict properly serializes a design task object."""
    now = datetime.now(timezone.utc)
    task = make_mock_design_task(
        task_id=SAMPLE_TASK_ID,
        design_no="D20260629-0042",
        status="designing",
        description="设计说明",
        design_file_url="https://example.com/design.pdf",
        client_comments="客户确认中",
        completed_at=None,
    )
    d = service._to_dict(task)
    assert d["id"] == str(SAMPLE_TASK_ID)
    assert d["design_no"] == "D20260629-0042"
    assert d["status"] == "designing"
    assert d["description"] == "设计说明"
    assert d["design_file_url"] == "https://example.com/design.pdf"
    assert d["client_comments"] == "客户确认中"
    assert d["completed_at"] is None
    assert isinstance(d["attachments"], list)


def test_to_dict_with_attachments(service):
    """_to_dict serializes attachment objects."""
    att = MagicMock()
    att.id = "att-1"
    att.related_type = "design_task"
    att.related_id = SAMPLE_TASK_ID
    att.filename = "sketch.ai"
    att.file_path = "202606/sketch.ai"
    att.file_size = 2048
    att.file_type = "application/illustrator"
    att.category = "design"
    att.uploaded_by = SAMPLE_USER_ID
    att.remark = "初稿"
    att.created_at = datetime.now(timezone.utc)

    task = make_mock_design_task(attachments=[att])
    d = service._to_dict(task)
    assert len(d["attachments"]) == 1
    assert d["attachments"][0]["filename"] == "sketch.ai"
    assert d["attachments"][0]["category"] == "design"


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
    task1 = make_mock_design_task(task_id=SAMPLE_TASK_ID, project_name="项目A")
    task2 = make_mock_design_task(
        task_id=SAMPLE_USER_ID,
        design_no="D20260629-0002",
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
    """create_task sets design_no, status, and returns serialized result."""

    async def create_side_effect(data):
        return make_mock_design_task(
            design_no="D20260629-0050",
            project_name=data.get("project_name", "默认"),
        )

    mock_repo.create.side_effect = create_side_effect

    with patch("app.services.task_service.generate_design_no", AsyncMock(return_value="D20260629-0050")):
        result = await service.create_task({
            "order_id": SAMPLE_TASK_ID,
            "customer_id": SAMPLE_USER_ID,
            "project_name": "新设计",
        })

    assert result["design_no"] == "D20260629-0050"
    assert result["project_name"] == "新设计"


# --- Update Task Tests ---

@pytest.mark.asyncio
async def test_update_task(service, mock_repo):
    """update_task modifies and returns updated task."""
    task = make_mock_design_task(project_name="旧名称")
    mock_repo.get_by_id.return_value = task
    mock_repo.update.return_value = make_mock_design_task(project_name="新名称")

    result = await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称"})
    assert result["project_name"] == "新名称"


@pytest.mark.asyncio
async def test_update_nonexistent_task(service, mock_repo):
    """update_task on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="设计任务不存在"):
        await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称"})
