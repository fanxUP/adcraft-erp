from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.employee import Employee

class EmployeeRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def get_by_id(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()
    async def list(self, skip=0, limit=20, keyword=None, department=None, employment_status=None):
        q = select(Employee).where(Employee.deleted_at.is_(None))
        if keyword: p = f"%{keyword}%"; q = q.where(or_(Employee.employee_no.ilike(p), Employee.name.ilike(p), Employee.phone.ilike(p)))
        if department: q = q.where(Employee.department == department)
        if employment_status: q = q.where(Employee.employment_status == employment_status)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(q.order_by(Employee.employee_no.asc()).offset(skip).limit(limit))
        return list(r.scalars().all()), t
    async def create(self, data): e = Employee(**data); self.db.add(e); await self.db.flush(); return e
    async def update(self, e, data):
        for k, v in data.items():
            if v is not None: setattr(e, k, v)
        await self.db.flush(); return e
    async def soft_delete(self, e): e.deleted_at = datetime.now(); await self.db.flush()