from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import Role, Permission, User, user_roles


class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(self) -> list[Role]:
        result = await self.db.execute(select(Role).order_by(Role.name))
        return list(result.scalars().all())

    async def get_by_id(self, role_id: UUID) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        await self.db.flush()
        return role

    async def update(self, role: Role, data: dict) -> Role:
        if "name" in data and data["name"]:
            role.name = data["name"].strip()
        if "description" in data:
            role.description = data["description"]
        await self.db.flush()
        return role

    async def delete(self, role: Role) -> None:
        await self.db.delete(role)
        await self.db.flush()

    async def get_permissions_by_ids(self, perm_ids: list[UUID]) -> list[Permission]:
        if not perm_ids:
            return []
        result = await self.db.execute(select(Permission).where(Permission.id.in_(perm_ids)))
        return list(result.scalars().all())

    async def set_permissions(self, role: Role, permissions: list[Permission]) -> None:
        role.permissions = permissions
        await self.db.flush()

    async def list_permissions(self) -> list[Permission]:
        result = await self.db.execute(select(Permission).order_by(Permission.code))
        return list(result.scalars().all())

    async def get_bound_users(self, role_id: UUID) -> list[User]:
        """Load active users and their complete role-permission union.

        Role edits are validated against the effective permissions of every
        affected user before the association table is changed.  Eager loading
        keeps that check deterministic and avoids a lazy-load after the
        request transaction has started mutating the role.
        """
        result = await self.db.execute(
            select(User)
            .join(user_roles, user_roles.c.user_id == User.id)
            .where(
                user_roles.c.role_id == role_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return list(result.scalars().unique().all())
