from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.employment_history import EmploymentHistory


class EmploymentHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, hid: UUID):
        r = await self.db.execute(select(EmploymentHistory).where(EmploymentHistory.id == hid))
        return r.scalar_one_or_none()

    async def list(self, skip=0, limit=20, employee_id=None, change_type=None):
        q = select(EmploymentHistory)
        if employee_id:
            q = q.where(EmploymentHistory.employee_id == employee_id)
        if change_type:
            q = q.where(EmploymentHistory.change_type == change_type)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(
            q.order_by(EmploymentHistory.change_date.desc()).offset(skip).limit(limit)
        )
        return list(r.scalars().all()), t

    async def create(self, data):
        e = EmploymentHistory(**data)
        self.db.add(e)
        await self.db.flush()
        return e

    async def update(self, e, data):
        for k, v in data.items():
            if v is not None:
                setattr(e, k, v)
        await self.db.flush()
        return e

    async def delete(self, e):
        await self.db.delete(e)
        await self.db.flush()
