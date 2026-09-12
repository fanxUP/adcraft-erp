"""Regression tests for per-user preferences and password safety rules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.user_preferences import UserPreference
from app.schemas.auth import ChangePasswordRequest, UserPreferencesUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from tests.conftest import SAMPLE_USER_ID


def make_user():
    user = MagicMock()
    user.id = SAMPLE_USER_ID
    user.username = "testuser"
    user.password_hash = "old_hash"
    user.is_active = True
    user.must_change_password = False
    user.real_name = "测试用户"
    user.phone = None
    user.email = None
    user.roles = []
    return user


def preference_result(preference=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = preference
    return result


@pytest.mark.asyncio
async def test_profile_includes_safe_default_preferences_when_record_is_missing():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[preference_result(make_user()), preference_result(None)])
    service = AuthService(db)

    profile = await service.get_profile(SAMPLE_USER_ID)

    assert profile["preferences"] == {
        "theme": "light-blue",
        "font_size": 14,
        "font_weight": 400,
    }
    created = db.add.await_args.args[0]
    assert isinstance(created, UserPreference)
    assert created.user_id == SAMPLE_USER_ID


@pytest.mark.asyncio
async def test_update_preferences_is_partial_and_targets_current_user_id():
    db = AsyncMock()
    existing = UserPreference(user_id=SAMPLE_USER_ID, theme="light-blue", font_size=14, font_weight=400)
    db.execute = AsyncMock(return_value=preference_result(existing))
    service = AuthService(db)

    updated = await service.update_preferences(SAMPLE_USER_ID, {"theme": "dark-blue"})

    assert updated == {"theme": "dark-blue", "font_size": 14, "font_weight": 400}
    assert existing.user_id == SAMPLE_USER_ID
    assert existing.font_size == 14
    assert existing.font_weight == 400


def test_preferences_schema_rejects_unregistered_values_and_empty_patch():
    with pytest.raises(ValidationError):
        UserPreferencesUpdate(theme="url(javascript:alert(1))")
    with pytest.raises(ValidationError):
        UserPreferencesUpdate(font_size=99)
    with pytest.raises(ValidationError):
        UserPreferencesUpdate()


def test_change_password_schema_rejects_unsafe_values():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="short")
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="same-password", new_password="same-password")
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old-password", new_password="x" * 129)


@pytest.mark.asyncio
async def test_change_password_rejects_same_password_and_clears_force_change_flag():
    db = AsyncMock()
    user = make_user()
    user.must_change_password = True
    db.execute = AsyncMock(return_value=preference_result(user))
    service = AuthService(db)

    with patch("app.services.auth_service.verify_password", return_value=True), \
         patch("app.services.auth_service.hash_password", return_value="new_hash"):
        with pytest.raises(ValueError, match="不能与原密码相同"):
            await service.change_password(SAMPLE_USER_ID, "same-password", "same-password")

        ok = await service.change_password(SAMPLE_USER_ID, "old-password", "new-password")

    assert ok is True
    assert user.must_change_password is False


@pytest.mark.asyncio
async def test_admin_reset_password_marks_user_for_forced_change():
    db = AsyncMock()
    user = make_user()
    db.execute = AsyncMock(return_value=preference_result(user))
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=user)
    repo.update = AsyncMock()
    with patch("app.services.user_service.UserRepository", return_value=repo), \
         patch("app.services.user_service.hash_password", return_value="reset_hash"):
        service = UserService(db)
        assert await service.reset_password(SAMPLE_USER_ID, "reset-password") is True

    assert user.password_hash == "reset_hash"
    assert user.must_change_password is True
