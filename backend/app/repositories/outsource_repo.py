import uuid as _uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.outsource import OutsourceVendor, OutsourceTask, OutsourcePayment


class OutsourceVendorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, vendor_id: UUID) -> OutsourceVendor | None:
        result = await self.db.execute(
            select(OutsourceVendor).where(OutsourceVendor.id == vendor_id, OutsourceVendor.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_vendors(self, skip: int = 0, limit: int = 20, keyword: str | None = None,
                           service_type: str | None = None) -> tuple[list[OutsourceVendor], int]:
        q = select(OutsourceVendor).where(OutsourceVendor.deleted_at.is_(None))
        if keyword:
            q = q.where(OutsourceVendor.name.ilike(f"%{keyword}%"))
        if service_type:
            q = q.where(OutsourceVendor.service_type == service_type)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourceVendor.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourceVendor:
        data.setdefault("id", _uuid.uuid4())
        vendor = OutsourceVendor(**data)
        self.db.add(vendor)
        await self.db.flush()
        return vendor

    async def update(self, vendor: OutsourceVendor, data: dict) -> OutsourceVendor:
        for k, v in data.items():
            if v is not None:
                setattr(vendor, k, v)
        await self.db.flush()
        return vendor

    async def soft_delete(self, vendor: OutsourceVendor) -> None:
        from datetime import datetime, timezone
        vendor.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()


class OutsourceTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: UUID) -> OutsourceTask | None:
        result = await self.db.execute(
            select(OutsourceTask).where(OutsourceTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(self, skip: int = 0, limit: int = 20, status: str | None = None,
                         vendor_id: UUID | None = None, order_id: UUID | None = None) -> tuple[list[OutsourceTask], int]:
        q = select(OutsourceTask)
        if status:
            q = q.where(OutsourceTask.status == status)
        if vendor_id:
            q = q.where(OutsourceTask.vendor_id == vendor_id)
        if order_id:
            q = q.where(OutsourceTask.order_id == order_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourceTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourceTask:
        data.setdefault("id", _uuid.uuid4())
        task = OutsourceTask(**data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update(self, task: OutsourceTask, data: dict) -> OutsourceTask:
        for k, v in data.items():
            if v is not None:
                setattr(task, k, v)
        await self.db.flush()
        return task


class OutsourcePaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_payments(self, skip: int = 0, limit: int = 20, vendor_id: UUID | None = None,
                            task_id: UUID | None = None) -> tuple[list[OutsourcePayment], int]:
        q = select(OutsourcePayment)
        if vendor_id:
            q = q.where(OutsourcePayment.vendor_id == vendor_id)
        if task_id:
            q = q.where(OutsourcePayment.task_id == task_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourcePayment.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourcePayment:
        data.setdefault("id", _uuid.uuid4())
        payment = OutsourcePayment(**data)
        self.db.add(payment)
        await self.db.flush()
        return payment
