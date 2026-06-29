"""Tests for UserService: CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.user_service import UserService
from tests.conftest import SAMPLE_USER_ID


def make_mock_user(**kwargs):
    """Create a mock User-like object."""
    now = datetime.now(timezone.utc)
    u = MagicMock()
    u.id = kwargs.get("id", SAMPLE_USER_ID)
    u.username = kwargs.get("username", "testuser")
    u.real_name = kwargs.get("real_name", "测试用户")
    u.phone = kwargs.get("phone", "13800138000")
    u.email = kwargs.get("email", "test@example.com")
    u.is_active = kwargs.get("is_active", True)
    u.password_hash = kwargs.get("password_hash", "hashed_pwd")
    u.created_at = kwargs.get("created_at", now)

    role_names = kwargs.get("role_names", ["admin"])
    role_mocks = []
    for rn in role_names:
        r = MagicMock()
        r.name = rn
        role_mocks.append(r)
    u.roles = role_mocks
    return u


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_username = AsyncMock(return_value=None)
    repo.list_users = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    repo.get_roles = AsyncMock(return_value=[])
    repo.set_roles = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    with patch("app.services.user_service.UserRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        svc = UserService(db)
        svc.repo = mock_repo
        yield svc


# --- List Tests ---

@pytest.mark.asyncio
async def test_list_users_empty(service, mock_repo):
    mock_repo.list_users.return_value = ([], 0)
    items, total = await service.list_users(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_users_with_results(service, mock_repo):
    u1 = make_mock_user(username="user1", real_name="用户A", role_names=["sales"])
    u2 = make_mock_user(id=SAMPLE_USER_ID, username="user2", real_name="用户B", role_names=["admin", "finance"])
    mock_repo.list_users.return_value = ([u1, u2], 2)

    items, total = await service.list_users(page=1, page_size=20)
    assert total == 2
    assert items[0]["username"] == "user1"
    assert items[0]["roles"] == ["sales"]
    assert items[1]["username"] == "user2"
    assert items[1]["roles"] == ["admin", "finance"]


# --- Get Tests ---

@pytest.mark.asyncio
async def test_get_user_found(service, mock_repo):
    u = make_mock_user()
    mock_repo.get_by_id.return_value = u

    result = await service.get_user(SAMPLE_USER_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_USER_ID)
    assert result["username"] == "testuser"
    assert result["real_name"] == "测试用户"
    assert result["is_active"] is True
    assert result["roles"] == ["admin"]


@pytest.mark.asyncio
async def test_get_user_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.get_user(SAMPLE_USER_ID)
    assert result is None


# --- Create Tests ---

@pytest.mark.asyncio
async def test_create_user_success(service, mock_repo):
    created_user = make_mock_user(username="newuser", real_name="新用户", role_names=[])
    mock_repo.create.return_value = created_user
    # create_user calls get_user after create, which calls repo.get_by_id
    mock_repo.get_by_id.return_value = created_user

    with patch("app.services.user_service.hash_password", return_value="hashed_new"):
        result = await service.create_user({
            "username": "newuser",
            "password": "NewPass123!",
            "real_name": "新用户",
        })

    assert result["username"] == "newuser"
    assert result["real_name"] == "新用户"
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_username(service, mock_repo):
    existing = make_mock_user(username="existing")
    mock_repo.get_by_username.return_value = existing

    with pytest.raises(ValueError, match="用户名已存在"):
        await service.create_user({"username": "existing", "password": "Pass123!"})


# --- Update Tests ---

@pytest.mark.asyncio
async def test_update_user(service, mock_repo):
    old_user = make_mock_user(real_name="旧名称")
    updated_user = make_mock_user(real_name="新名称")
    # First call (in update_user) -> old_user; second call (in get_user) -> updated_user
    mock_repo.get_by_id.side_effect = [old_user, updated_user]
    mock_repo.update.return_value = updated_user

    result = await service.update_user(SAMPLE_USER_ID, {"real_name": "新名称"})
    assert result["real_name"] == "新名称"


@pytest.mark.asyncio
async def test_update_user_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="用户不存在"):
        await service.update_user(SAMPLE_USER_ID, {"real_name": "新名称"})


# --- Delete Tests ---

@pytest.mark.asyncio
async def test_delete_user_success(service, mock_repo):
    u = make_mock_user()
    mock_repo.get_by_id.return_value = u

    result = await service.delete_user(SAMPLE_USER_ID)
    assert result is True
    mock_repo.soft_delete.assert_awaited_once_with(u)


@pytest.mark.asyncio
async def test_delete_user_not_found(service, mock_repo):
    mock_repo.get_by_id.return_value = None
    result = await service.delete_user(SAMPLE_USER_ID)
    assert result is False
