from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    ROLE_ADMIN,
    ROLE_DESIGNER,
    ROLE_FINANCE,
    ROLE_INSTALLER,
    ROLE_PRODUCTION,
    ROLE_RESOURCE_MANAGER,
    ROLE_OUTSOURCE_MANAGER,
    ROLE_SALES,
    validate_role_resource_permissions,
    validate_role_sensitive_permissions,
)
from app.repositories.role_repo import RoleRepository


BUILTIN_ROLE_NAMES = frozenset({
    ROLE_ADMIN,
    ROLE_SALES,
    ROLE_DESIGNER,
    ROLE_PRODUCTION,
    ROLE_INSTALLER,
    ROLE_FINANCE,
    ROLE_RESOURCE_MANAGER,
    ROLE_OUTSOURCE_MANAGER,
})


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
        if name in BUILTIN_ROLE_NAMES:
            raise ValueError("该名称属于系统内置角色，不能重复创建")
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValueError("角色名称已存在")
        role = await self.repo.create(name, description)
        return {"id": str(role.id), "name": role.name, "description": role.description, "permissions": []}

    async def update_role(self, role_id: UUID, data: dict) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        requested_name = data.get("name")
        if requested_name:
            requested_name = requested_name.strip()
            if requested_name != role.name:
                if role.name in BUILTIN_ROLE_NAMES:
                    raise ValueError("系统内置角色不能重命名")
                if requested_name in BUILTIN_ROLE_NAMES:
                    raise ValueError("该名称属于系统内置角色，不能使用")
                duplicate = await self.repo.get_by_name(requested_name)
                if duplicate and duplicate.id != role.id:
                    raise ValueError("角色名称已存在")
                data = {**data, "name": requested_name}
        role = await self.repo.update(role, data)
        return {"id": str(role.id), "name": role.name, "description": role.description}

    async def delete_role(self, role_id: UUID) -> None:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        if role.name in BUILTIN_ROLE_NAMES:
            raise ValueError("系统内置角色不能删除")
        await self.repo.delete(role)

    async def set_role_permissions(self, role_id: UUID, permission_ids: list[str]) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        try:
            perm_uuids = list(dict.fromkeys(UUID(pid) for pid in permission_ids))
        except (AttributeError, TypeError, ValueError):
            raise ValueError("权限编号格式不正确")
        perms = await self.repo.get_permissions_by_ids(perm_uuids)
        if len(perms) != len(perm_uuids):
            raise ValueError("存在无效权限编号，未保存本次变更")
        validate_role_sensitive_permissions(role.name, {permission.code for permission in perms})
        validate_role_resource_permissions(role.name, {permission.code for permission in perms})
        await self.repo.set_permissions(role, perms)
        return {
            "id": str(role.id),
            "name": role.name,
            "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in role.permissions],
        }

    async def list_permissions(self) -> list[dict]:
        perms = await self.repo.list_permissions()
        return [{"id": str(p.id), "code": p.code, "name": p.name, "description": p.description} for p in perms]
