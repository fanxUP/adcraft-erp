from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exists, func, or_, select

from app.models.employee import Employee
from app.models.user import User, Role


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str, *, include_deleted: bool = False) -> User | None:
        query = select(User).where(User.username == username)
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_users(self, skip: int = 0, limit: int = 20, keyword: str | None = None) -> tuple[list[User], int]:
        q = select(User).where(User.deleted_at.is_(None))
        if keyword:
            pattern = f"%{keyword}%"
            employee_match = exists(
                select(Employee.id).where(
                    Employee.user_id == User.id,
                    Employee.deleted_at.is_(None),
                    or_(
                        Employee.employee_no.ilike(pattern),
                        Employee.name.ilike(pattern),
                    ),
                )
            )
            q = q.where(
                or_(
                    User.username.ilike(pattern),
                    User.real_name.ilike(pattern),
                    employee_match,
                )
            )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User, update_data: dict) -> User:
        for key, value in update_data.items():
            if key != "role_ids":
                setattr(user, key, value)
        await self.db.flush()
        return user

    async def soft_delete(self, user: User) -> User:
        from datetime import datetime
        user.deleted_at = datetime.now()
        await self.db.flush()
        return user

    async def get_roles(self, role_ids: list[UUID]) -> list[Role]:
        if not role_ids:
            return []
        result = await self.db.execute(select(Role).where(Role.id.in_(role_ids)))
        return list(result.scalars().all())

    async def set_roles(self, user: User, roles: list[Role]) -> User:
        user.roles = roles
        await self.db.flush()
        return user

    async def get_all_active_users(self, exclude_user_id: UUID | None = None) -> list[User]:
        """获取所有活跃用户（会话列表用）"""
        q = select(User).where(User.deleted_at.is_(None), User.is_active.is_(True))
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
        q = q.order_by(User.username)
        result = await self.db.execute(q)
        return list(result.scalars().all())
