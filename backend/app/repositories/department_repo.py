from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.department import Department


class DepartmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, did: UUID):
        r = await self.db.execute(
            select(Department).where(Department.id == did, Department.deleted_at.is_(None))
        )
        return r.scalar_one_or_none()

    async def list(self, keyword=None, parent_id=None, include_inactive=False):
        q = select(Department).where(Department.deleted_at.is_(None))
        if not include_inactive:
            q = q.where(Department.is_active == True)
        if keyword:
            p = f"%{keyword}%"
            q = q.where(or_(Department.name.ilike(p), Department.code.ilike(p)))
        if parent_id is not None:
            q = q.where(Department.parent_id == parent_id)
        r = await self.db.execute(q.order_by(Department.sort_order.asc(), Department.name.asc()))
        return list(r.scalars().all())

    async def get_by_code(self, code: str):
        r = await self.db.execute(
            select(Department).where(Department.code == code, Department.deleted_at.is_(None))
        )
        return r.scalar_one_or_none()

    async def create(self, data):
        d = Department(**data)
        self.db.add(d)
        await self.db.flush()
        return d

    async def update(self, d, data):
        for k, v in data.items():
            if v is not None:
                setattr(d, k, v)
        await self.db.flush()
        return d

    async def soft_delete(self, d):
        d.deleted_at = datetime.now()
        await self.db.flush()
