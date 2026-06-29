from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repo import UserRepository
from app.utils.security import hash_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def list_users(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        users, total = await self.repo.list_users(skip=skip, limit=page_size, keyword=keyword)
        user_list = []
        for u in users:
            user_list.append({
                "id": str(u.id),
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "email": u.email,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "roles": [r.name for r in u.roles],
            })
        return user_list, total

    async def get_user(self, user_id: UUID) -> dict | None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None
        return {
            "id": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "roles": [r.name for r in user.roles],
        }

    async def create_user(self, data: dict) -> dict:
        existing = await self.repo.get_by_username(data["username"])
        if existing:
            raise ValueError("用户名已存在")

        role_ids = data.pop("role_ids", [])
        if role_ids:
            role_ids_uuid = [UUID(rid) for rid in role_ids]
            roles = await self.repo.get_roles(role_ids_uuid)
        else:
            roles = []

        data["password_hash"] = hash_password(data.pop("password"))
        user = await self.repo.create(data)
        if roles:
            await self.repo.set_roles(user, roles)

        return await self.get_user(user.id)

    async def update_user(self, user_id: UUID, data: dict) -> dict:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        role_ids = data.pop("role_ids", None)
        await self.repo.update(user, data)

        if role_ids is not None:
            roles = await self.repo.get_roles([UUID(rid) for rid in role_ids])
            await self.repo.set_roles(user, roles)

        return await self.get_user(user.id)

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        await self.repo.soft_delete(user)
        return True
