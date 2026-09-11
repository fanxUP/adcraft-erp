from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permission_catalog import validate_permission_set
from app.repositories.user_repo import UserRepository
from app.utils.security import hash_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    @staticmethod
    def _validate_roles(role_ids: list[str], roles: list) -> None:
        """Validate role references and the effective capability composition.

        Role names are labels only.  The effective permission union is the
        security input, so custom roles behave exactly like built-in roles.
        """
        try:
            requested_ids = {str(UUID(role_id)) for role_id in role_ids}
        except (AttributeError, TypeError, ValueError):
            raise ValueError("角色编号格式不正确")
        loaded_ids = {str(role.id) for role in roles}
        if requested_ids != loaded_ids:
            raise ValueError("存在无效角色编号，未保存本次角色变更")

        effective_codes = {
            permission.code
            for role in roles
            for permission in getattr(role, "permissions", ())
        }
        issues = validate_permission_set(effective_codes)
        if issues:
            raise ValueError("；".join(dict.fromkeys(issue.message for issue in issues)))

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
        self._validate_roles(role_ids, roles)

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
        roles = None
        if role_ids is not None:
            try:
                role_ids_uuid = [UUID(rid) for rid in role_ids]
            except (AttributeError, TypeError, ValueError):
                raise ValueError("角色编号格式不正确")
            roles = await self.repo.get_roles(role_ids_uuid)
            self._validate_roles(role_ids, roles)

        # Validate the complete role set before changing any user fields.  A
        # rejected combination must not leave a partially mutated user in a
        # service call that is not wrapped by the HTTP transaction boundary.
        await self.repo.update(user, data)
        if roles is not None:
            await self.repo.set_roles(user, roles)

        return await self.get_user(user.id)

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        await self.repo.soft_delete(user)
        return True

    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        user.password_hash = hash_password(new_password)
        await self.repo.update(user, {})
        return True
