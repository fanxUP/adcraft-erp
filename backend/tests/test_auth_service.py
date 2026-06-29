"""Tests for AuthService: authenticate, profile, change_password."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService
from tests.conftest import SAMPLE_USER_ID


def make_mock_user(**kwargs):
    """Create a mock User-like object for auth tests."""
    u = MagicMock()
    u.id = kwargs.get("id", SAMPLE_USER_ID)
    u.username = kwargs.get("username", "testuser")
    u.password_hash = kwargs.get("password_hash", "hashed_pwd")
    u.is_active = kwargs.get("is_active", True)
    u.real_name = kwargs.get("real_name", "测试用户")
    u.phone = kwargs.get("phone", "13800138000")
    u.email = kwargs.get("email", "test@example.com")
    u.created_at = kwargs.get("created_at")
    role_names = kwargs.get("role_names", ["admin"])
    roles = []
    for rn in role_names:
        r = MagicMock()
        r.name = rn
        roles.append(r)
    u.roles = roles
    return u


@pytest.fixture
def service():
    """Create AuthService with a mocked database session."""
    db = AsyncMock()
    return AuthService(db)


@pytest.mark.asyncio
async def test_authenticate_success(service):
    """Successful authentication returns user and token."""
    user = make_mock_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    with patch("app.services.auth_service.verify_password", return_value=True), \
         patch("app.services.auth_service.create_access_token", return_value="fake-jwt-token"):
        outcome = await service.authenticate(LoginRequest(username="testuser", password="correct"))

    assert outcome is not None
    assert outcome[0] is user
    assert outcome[1] == "fake-jwt-token"


@pytest.mark.asyncio
async def test_authenticate_user_not_found(service):
    """Authentication fails when user does not exist."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    service.db.execute = AsyncMock(return_value=result)

    outcome = await service.authenticate(LoginRequest(username="nobody", password="pass"))
    assert outcome is None


@pytest.mark.asyncio
async def test_authenticate_inactive_user(service):
    """Authentication fails when user is inactive."""
    user = make_mock_user(is_active=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    outcome = await service.authenticate(LoginRequest(username="inactive", password="pass"))
    assert outcome is None


@pytest.mark.asyncio
async def test_authenticate_wrong_password(service):
    """Authentication fails with incorrect password."""
    user = make_mock_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    with patch("app.services.auth_service.verify_password", return_value=False):
        outcome = await service.authenticate(LoginRequest(username="testuser", password="wrong"))

    assert outcome is None


# --- Profile Tests ---

@pytest.mark.asyncio
async def test_get_profile_found(service):
    user = make_mock_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    profile = await service.get_profile(SAMPLE_USER_ID)
    assert profile is not None
    assert profile["username"] == "testuser"
    assert profile["real_name"] == "测试用户"
    assert profile["is_active"] is True
    assert profile["roles"] == ["admin"]


@pytest.mark.asyncio
async def test_get_profile_not_found(service):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    service.db.execute = AsyncMock(return_value=result)

    profile = await service.get_profile(SAMPLE_USER_ID)
    assert profile is None


# --- Change Password Tests ---

@pytest.mark.asyncio
async def test_change_password_success(service):
    user = make_mock_user(password_hash="old_hash")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    with patch("app.services.auth_service.verify_password", side_effect=lambda pwd, h: pwd == "old_pass"), \
         patch("app.services.auth_service.hash_password", return_value="new_hash"):
        ok = await service.change_password(SAMPLE_USER_ID, "old_pass", "new_pass")

    assert ok is True
    assert user.password_hash == "new_hash"
    service.db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(service):
    user = make_mock_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    service.db.execute = AsyncMock(return_value=result)

    with patch("app.services.auth_service.verify_password", return_value=False):
        ok = await service.change_password(SAMPLE_USER_ID, "wrong_old", "new_pass")

    assert ok is False


@pytest.mark.asyncio
async def test_change_password_user_not_found(service):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    service.db.execute = AsyncMock(return_value=result)

    ok = await service.change_password(SAMPLE_USER_ID, "old_pass", "new_pass")
    assert ok is False
