from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.leave import LeaveRequest


class LeaveRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, lid: UUID):
        r = await self.db.execute(select(LeaveRequest).where(LeaveRequest.id == lid))
        return r.scalar_one_or_none()

    async def list(self, skip=0, limit=20, employee_id=None, status=None, leave_type=None):
        q = select(LeaveRequest)
        if employee_id:
            q = q.where(LeaveRequest.employee_id == employee_id)
        if status:
            q = q.where(LeaveRequest.status == status)
        if leave_type:
            q = q.where(LeaveRequest.leave_type == leave_type)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(
            q.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit)
        )
        return list(r.scalars().all()), t

    async def create(self, data):
        l = LeaveRequest(**data)
        self.db.add(l)
        await self.db.flush()
        return l

    async def update(self, l, data):
        for k, v in data.items():
            if v is not None:
                setattr(l, k, v)
        await self.db.flush()
        return l

    async def delete(self, l):
        await self.db.delete(l)
        await self.db.flush()
