from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.operation_log import OperationLog


class OperationLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, log_id: UUID) -> OperationLog | None:
        result = await self.db.execute(select(OperationLog).where(OperationLog.id == log_id))
        return result.scalar_one_or_none()

    async def list_logs(
        self,
        skip: int = 0,
        limit: int = 20,
        user_id: UUID | None = None,
        object_type: str | None = None,
        action: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[OperationLog], int]:
        conditions = []
        if user_id:
            conditions.append(OperationLog.user_id == user_id)
        if object_type:
            conditions.append(OperationLog.object_type == object_type)
        if action:
            conditions.append(OperationLog.action.ilike(f"%{action}%"))
        if date_from:
            conditions.append(OperationLog.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conditions.append(OperationLog.created_at <= datetime.combine(date_to, datetime.max.time()))

        q = select(OperationLog)
        if conditions:
            q = q.where(and_(*conditions))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OperationLog:
        log = OperationLog(**data)
        self.db.add(log)
        await self.db.flush()
        return log
