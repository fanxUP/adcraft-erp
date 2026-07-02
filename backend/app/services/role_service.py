from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.role_repo import RoleRepository


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RoleRepository(db)

    async def list_roles(self) -> list[dict]:
        roles = await self.repo.list_roles()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in r.permissions],
            }
            for r in roles
        ]

    async def create_role(self, name: str, description: str | None = None) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("角色名称不能为空")
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValueError("角色名称已存在")
        role = await self.repo.create(name, description)
        return {"id": str(role.id), "name": role.name, "description": role.description, "permissions": []}

    async def update_role(self, role_id: UUID, data: dict) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        role = await self.repo.update(role, data)
        return {"id": str(role.id), "name": role.name, "description": role.description}

    async def delete_role(self, role_id: UUID) -> None:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        if role.name == "admin":
            raise ValueError("不能删除 admin 角色")
        await self.repo.delete(role)

    async def set_role_permissions(self, role_id: UUID, permission_ids: list[str]) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        perm_uuids = [UUID(pid) for pid in permission_ids]
        perms = await self.repo.get_permissions_by_ids(perm_uuids)
        await self.repo.set_permissions(role, perms)
        return {
            "id": str(role.id),
            "name": role.name,
            "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in role.permissions],
        }

    async def list_permissions(self) -> list[dict]:
        perms = await self.repo.list_permissions()
        return [{"id": str(p.id), "code": p.code, "name": p.name, "description": p.description} for p in perms]
