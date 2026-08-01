from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.salary_rule import SalaryRule


class SalaryRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, rid: UUID):
        r = await self.db.execute(select(SalaryRule).where(SalaryRule.id == rid))
        return r.scalar_one_or_none()

    async def get_by_employee(self, employee_id: UUID):
        r = await self.db.execute(
            select(SalaryRule).where(SalaryRule.employee_id == employee_id)
            .order_by(SalaryRule.effective_date.desc())
        )
        return r.scalars().all()

    async def list(self, skip=0, limit=20, employee_id=None):
        q = select(SalaryRule)
        if employee_id:
            q = q.where(SalaryRule.employee_id == employee_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(
            q.order_by(SalaryRule.effective_date.desc(), SalaryRule.employee_id.asc())
            .offset(skip).limit(limit)
        )
        return list(r.scalars().all()), total

    async def create(self, data):
        obj = SalaryRule(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, obj, data):
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)  # 服务端 onupdate(func.now()) 会过期 updated_at，需异步刷新
        return obj

    async def delete(self, obj):
        await self.db.delete(obj)
        await self.db.flush()
