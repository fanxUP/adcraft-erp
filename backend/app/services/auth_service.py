from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.user import User, Role
from app.schemas.auth import LoginRequest
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
        token = create_access_token(user.id, user.username)
        return user, token

    async def get_profile(self, user_id: UUID) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "id": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "is_active": user.is_active,
            "roles": [r.name for r in user.roles],
        }

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        if not verify_password(old_password, user.password_hash):
            return False
        user.password_hash = hash_password(new_password)
        await self.db.flush()
        return True
