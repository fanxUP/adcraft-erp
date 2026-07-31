from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, asc
from app.models.salary import SalaryRecord


class SalaryRecordRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, sid: UUID):
        r = await self.db.execute(select(SalaryRecord).where(SalaryRecord.id == sid))
        return r.scalar_one_or_none()

    async def get_by_employee_month(self, employee_id: UUID, month: str):
        r = await self.db.execute(
            select(SalaryRecord).where(SalaryRecord.employee_id == employee_id, SalaryRecord.month == month)
        )
        return r.scalars().first()

    async def list(self, skip=0, limit=20, employee_id=None, month=None, payment_status=None):
        q = select(SalaryRecord)
        if employee_id:
            q = q.where(SalaryRecord.employee_id == employee_id)
        if month:
            q = q.where(SalaryRecord.month == month)
        if payment_status:
            q = q.where(SalaryRecord.payment_status == payment_status)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(
            q.order_by(SalaryRecord.month.desc(), SalaryRecord.employee_id.asc())
            .offset(skip).limit(limit)
        )
        return list(r.scalars().all()), t

    async def create(self, data):
        s = SalaryRecord(**data)
        self.db.add(s)
        await self.db.flush()
        return s

    async def update(self, s, data):
        for k, v in data.items():
            if v is not None:
                setattr(s, k, v)
        await self.db.flush()
        return s

    async def delete(self, s):
        await self.db.delete(s)
        await self.db.flush()
