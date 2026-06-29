"""Tests for OperationLogService and log_operation utility."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.operation_log_service import OperationLogService, log_operation
from tests.conftest import SAMPLE_USER_ID


def make_mock_log(**kwargs):
    now = datetime.now(timezone.utc)
    log = MagicMock()
    log.id = kwargs.get("id", SAMPLE_USER_ID)
    log.user_id = kwargs.get("user_id", SAMPLE_USER_ID)
    log.user_name = kwargs.get("user_name", "管理员")
    log.object_type = kwargs.get("object_type", "order")
    log.object_id = kwargs.get("object_id", SAMPLE_USER_ID)
    log.action = kwargs.get("action", "create")
    log.before_data = kwargs.get("before_data")
    log.after_data = kwargs.get("after_data")
    log.ip_address = kwargs.get("ip_address", "127.0.0.1")
    log.created_at = kwargs.get("created_at", now)
    return log


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_logs = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.operation_log_service.OperationLogRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = OperationLogService(db)
        svc.repo = mock_repo
        yield svc


# --- List Tests ---

@pytest.mark.asyncio
async def test_list_logs_empty(service, mock_repo):
    mock_repo.list_logs.return_value = ([], 0)
    items, total = await service.list_logs(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_logs_with_results(service, mock_repo):
    l1 = make_mock_log(action="create")
    l2 = make_mock_log(action="update")
    mock_repo.list_logs.return_value = ([l1, l2], 2)

    items, total = await service.list_logs(page=1, page_size=20)
    assert total == 2
    assert items[0]["action"] == "create"
    assert items[1]["action"] == "update"


# --- Get Tests ---

@pytest.mark.asyncio
async def test_get_log_found(service, mock_repo):
    log = make_mock_log()
    mock_repo.get_by_id.return_value = log
    result = await service.get_log(SAMPLE_USER_ID)
    assert result is not None
    assert result["action"] == "create"
    assert result["object_type"] == "order"
    assert result["user_name"] == "管理员"


@pytest.mark.asyncio
async def test_get_log_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.get_log(SAMPLE_USER_ID)
    assert result is None


# --- log_operation utility ---

@pytest.mark.asyncio
async def test_log_operation_utility():
    """The standalone log_operation function creates a log via Repository."""
    db = AsyncMock()
    mock_repo_instance = MagicMock()
    mock_repo_instance.create = AsyncMock()

    with patch("app.services.operation_log_service.OperationLogRepository", return_value=mock_repo_instance):
        await log_operation(
            db=db,
            user_id=SAMPLE_USER_ID,
            user_name="测试用户",
            object_type="order",
            object_id=SAMPLE_USER_ID,
            action="create",
            ip_address="192.168.1.1",
        )

    mock_repo_instance.create.assert_awaited_once()
    args = mock_repo_instance.create.call_args[0][0]
    assert args["user_id"] == SAMPLE_USER_ID
    assert args["user_name"] == "测试用户"
    assert args["object_type"] == "order"
    assert args["action"] == "create"
    assert args["ip_address"] == "192.168.1.1"
