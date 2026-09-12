from inspect import isawaitable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.user import User
from app.models.user_preferences import UserPreference
from app.core.permissions import get_user_capabilities, get_user_permission_codes
from app.core.password_policy import MAX_PASSWORD_LENGTH, validate_new_password
from app.schemas.auth import (
    DEFAULT_USER_PREFERENCES,
    FONT_SIZE_VALUES,
    FONT_WEIGHT_VALUES,
    THEME_VALUES,
    LoginRequest,
)
from app.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, data: LoginRequest) -> tuple[User, str] | None:
        result = await self.db.execute(select(User).where(User.username == data.username))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not verify_password(data.password, user.password_hash):
            return None
        token = create_access_token(user.id, user.username, token_version=user.token_version)
        return user, token

    async def get_profile(self, user_id: UUID) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        preferences = await self._ensure_preferences(user.id)
        return {
            "id": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "is_active": user.is_active,
            "must_change_password": user.must_change_password,
            "roles": [r.name for r in user.roles],
            "permissions": sorted(get_user_permission_codes(user)),
            "capabilities": get_user_capabilities(user),
            "preferences": preferences,
        }

    @staticmethod
    def _preference_payload(preference) -> dict | None:
        """Return only a validated preference shape from a model-like value."""
        if preference is None:
            return None
        try:
            theme = preference.theme
            font_size = preference.font_size
            font_weight = preference.font_weight
        except AttributeError:
            return None
        if (
            not isinstance(theme, str)
            or theme not in THEME_VALUES
            or isinstance(font_size, bool)
            or font_size not in FONT_SIZE_VALUES
            or isinstance(font_weight, bool)
            or font_weight not in FONT_WEIGHT_VALUES
        ):
            return None
        return {
            "theme": theme,
            "font_size": int(font_size),
            "font_weight": int(font_weight),
        }

    async def _add_and_flush(self, instance) -> None:
        # AsyncMock-based service tests expose ``add`` as awaitable, while a
        # real SQLAlchemy AsyncSession keeps ``add`` synchronous.  Supporting
        # both keeps the persistence path explicit without hiding failures.
        added = self.db.add(instance)
        if isawaitable(added):
            await added
        await self.db.flush()

    async def _ensure_preferences(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preference = result.scalar_one_or_none()
        payload = self._preference_payload(preference)
        if payload is not None:
            return payload

        if isinstance(preference, UserPreference):
            # Repair only an invalid preference row; never accept arbitrary
            # CSS/number values from a legacy or manually altered database.
            preference.theme = DEFAULT_USER_PREFERENCES["theme"]
            preference.font_size = DEFAULT_USER_PREFERENCES["font_size"]
            preference.font_weight = DEFAULT_USER_PREFERENCES["font_weight"]
            await self.db.flush()
            return dict(DEFAULT_USER_PREFERENCES)

        preference = UserPreference(
            user_id=user_id,
            theme=DEFAULT_USER_PREFERENCES["theme"],
            font_size=DEFAULT_USER_PREFERENCES["font_size"],
            font_weight=DEFAULT_USER_PREFERENCES["font_weight"],
        )
        await self._add_and_flush(preference)
        return dict(DEFAULT_USER_PREFERENCES)

    async def update_preferences(self, user_id: UUID, updates: dict) -> dict | None:
        """Update only the authenticated user's allow-listed preferences."""
        if not updates:
            raise ValueError("至少需要设置一项个人偏好")
        unknown = set(updates) - {"theme", "font_size", "font_weight"}
        if unknown:
            raise ValueError("个人偏好字段不受支持")
        if "theme" in updates and updates["theme"] not in THEME_VALUES:
            raise ValueError("界面风格不受支持")
        if "font_size" in updates and updates["font_size"] not in FONT_SIZE_VALUES:
            raise ValueError("文字大小不受支持")
        if "font_weight" in updates and updates["font_weight"] not in FONT_WEIGHT_VALUES:
            raise ValueError("文字粗细不受支持")

        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preference = result.scalar_one_or_none()
        if isinstance(preference, UserPreference):
            if self._preference_payload(preference) is None:
                preference.theme = DEFAULT_USER_PREFERENCES["theme"]
                preference.font_size = DEFAULT_USER_PREFERENCES["font_size"]
                preference.font_weight = DEFAULT_USER_PREFERENCES["font_weight"]
        else:
            preference = UserPreference(
                user_id=user_id,
                theme=DEFAULT_USER_PREFERENCES["theme"],
                font_size=DEFAULT_USER_PREFERENCES["font_size"],
                font_weight=DEFAULT_USER_PREFERENCES["font_weight"],
            )
            await self._add_and_flush(preference)
        for field in ("theme", "font_size", "font_weight"):
            if field in updates:
                setattr(preference, field, updates[field])
        await self.db.flush()
        return self._preference_payload(preference) or dict(DEFAULT_USER_PREFERENCES)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        if not isinstance(old_password, str) or not old_password or len(old_password) > MAX_PASSWORD_LENGTH:
            return False
        validate_new_password(new_password)
        if old_password == new_password:
            raise ValueError("新密码不能与原密码相同")
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        if not verify_password(old_password, user.password_hash):
            return False
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        await self.db.flush()
        return True
