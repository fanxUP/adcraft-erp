"""Tests for installation task service: status transitions, CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.task_service import InstallationTaskService
from tests.conftest import (
    SAMPLE_TASK_ID,
    SAMPLE_USER_ID,
    make_mock_installation_task,
)


@pytest.fixture
def mock_repo():
    """Create a mock InstallationTaskRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.create = AsyncMock()
    repo.list_tasks = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def service(mock_repo):
    """Create InstallationTaskService with a mocked repository."""
    with patch("app.services.task_service.InstallationTaskRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = InstallationTaskService(db)
        # Override the repo created in __init__ with our mock
        svc.repo = mock_repo
        yield svc


# --- Status Transition Tests ---

TRANSITION_TABLE = [
    ("pending", "assigned", True),
    ("pending", "in_progress", True),
    ("pending", "pending_acceptance", False),
    ("pending", "completed", False),
    ("assigned", "in_progress", True),
    ("assigned", "pending", True),
    ("assigned", "completed", False),
    ("in_progress", "pending_acceptance", True),
    ("in_progress", "pending", True),
    ("in_progress", "completed", False),
    ("in_progress", "assigned", False),
    ("pending_acceptance", "completed", True),
    ("pending_acceptance", "in_progress", True),
    ("pending_acceptance", "assigned", False),
    ("completed", "in_progress", False),
    ("completed", "pending", False),
    ("completed", "assigned", False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status,should_succeed", TRANSITION_TABLE)
async def test_status_transitions(service, mock_repo, from_status, to_status, should_succeed):
    """Verify all allowed and forbidden status transitions."""
    task = make_mock_installation_task(status=from_status)
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
    task = make_mock_installation_task(status="pending_acceptance")
    mock_repo.get_by_id.return_value = task

    result = await service.change_status(SAMPLE_TASK_ID, "completed", SAMPLE_USER_ID)

    assert result["status"] == "completed"
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_change_status_nonexistent_task(service, mock_repo):
    """Changing status on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="安装任务不存在"):
        await service.change_status(SAMPLE_TASK_ID, "in_progress", SAMPLE_USER_ID)


# --- Get Task Tests ---

@pytest.mark.asyncio
async def test_get_task_found(service, mock_repo):
    """get_task returns correct data for an existing task."""
    task = make_mock_installation_task()
    mock_repo.get_by_id.return_value = task

    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_TASK_ID)
    assert result["installation_no"] == "I20260629-0001"
    assert result["project_name"] == "测试安装任务"
    assert result["status"] == "pending"
    assert result["address"] == "北京市朝阳区测试路100号"
    assert result["contact_name"] == "张三"
    assert result["contact_phone"] == "13800138000"


@pytest.mark.asyncio
async def test_get_task_not_found(service, mock_repo):
    """get_task returns None for a non-existent task."""
    mock_repo.get_by_id.return_value = None
    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is None


# --- To Dict Serialization ---

def test_to_dict_includes_all_fields(service):
    """_to_dict properly serializes a task object."""
    now = datetime.now(timezone.utc)
    task = make_mock_installation_task(
        task_id=SAMPLE_TASK_ID,
        installation_no="I20260629-0042",
        status="in_progress",
        scheduled_at=now,
        completed_at=None,
    )
    d = service._to_dict(task)
    assert d["id"] == str(SAMPLE_TASK_ID)
    assert d["installation_no"] == "I20260629-0042"
    assert d["status"] == "in_progress"
    assert d["scheduled_at"] == now.isoformat()
    assert d["completed_at"] is None
    assert isinstance(d["attachments"], list)


def test_to_dict_with_attachments(service):
    """_to_dict serializes attachment objects."""
    att = MagicMock()
    att.id = "att-1"
    att.related_type = "installation_task"
    att.related_id = SAMPLE_TASK_ID
    att.filename = "photo.jpg"
    att.file_path = "202606/abc.jpg"
    att.file_size = 1024
    att.file_type = "image/jpeg"
    att.category = "photo"
    att.uploaded_by = SAMPLE_USER_ID
    att.remark = None
    att.created_at = datetime.now(timezone.utc)

    task = make_mock_installation_task(attachments=[att])
    d = service._to_dict(task)
    assert len(d["attachments"]) == 1
    assert d["attachments"][0]["filename"] == "photo.jpg"
    assert d["attachments"][0]["file_path"] == "202606/abc.jpg"


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
    task1 = make_mock_installation_task(task_id=SAMPLE_TASK_ID, project_name="任务A")
    task2 = make_mock_installation_task(
        task_id=SAMPLE_USER_ID,  # Different UUID for second task
        installation_no="I20260629-0002",
        project_name="任务B",
    )
    mock_repo.list_tasks.return_value = ([task1, task2], 2)

    tasks, total = await service.list_tasks(page=1, page_size=20)
    assert total == 2
    assert len(tasks) == 2
    assert tasks[0]["project_name"] == "任务A"
    assert tasks[1]["project_name"] == "任务B"
