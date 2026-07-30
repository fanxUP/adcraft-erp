from uuid import UUID; from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession; from sqlalchemy import select, func
from app.models.attendance import AttendanceRule, AttendanceRecord

class AttendanceRuleRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def list(self): r = await self.db.execute(select(AttendanceRule).order_by(AttendanceRule.name.asc())); return list(r.scalars().all())
    async def get_by_id(self, rid): r = await self.db.execute(select(AttendanceRule).where(AttendanceRule.id == rid)); return r.scalar_one_or_none()
    async def create(self, d): o = AttendanceRule(**d); self.db.add(o); await self.db.flush(); return o
    async def update(self, o, d):
        for k,v in d.items():
            if v is not None: setattr(o,k,v)
        await self.db.flush(); return o
    async def delete(self, o): await self.db.delete(o); await self.db.flush()

class AttendanceRecordRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def list(self, skip=0, limit=20, employee_id=None, date_from=None, date_to=None):
        q = select(AttendanceRecord)
        if employee_id: q = q.where(AttendanceRecord.employee_id == employee_id)
        if date_from: q = q.where(AttendanceRecord.date >= date_from)
        if date_to: q = q.where(AttendanceRecord.date <= date_to)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(q.order_by(AttendanceRecord.date.desc()).offset(skip).limit(limit))
        return list(r.scalars().all()), t
    async def get_by_id(self, rid): r = await self.db.execute(select(AttendanceRecord).where(AttendanceRecord.id == rid)); return r.scalar_one_or_none()
    async def create(self, d): o = AttendanceRecord(**d); self.db.add(o); await self.db.flush(); return o
    async def update(self, o, d):
        for k,v in d.items():
            if v is not None: setattr(o,k,v)
        await self.db.flush(); await self.db.refresh(o); return o
    async def delete(self, o): await self.db.delete(o); await self.db.flush()