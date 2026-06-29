from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.task import DesignTask, ProductionTask, InstallationTask, Attachment


class DesignTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: UUID) -> DesignTask | None:
        result = await self.db.execute(select(DesignTask).where(DesignTask.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks(self, skip: int = 0, limit: int = 20, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list[DesignTask], int]:
        q = select(DesignTask)
        if status:
            q = q.where(DesignTask.status == status)
        if order_id:
            q = q.where(DesignTask.order_id == UUID(order_id))
        if assigned_to:
            q = q.where(DesignTask.assigned_to == UUID(assigned_to))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(DesignTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> DesignTask:
        task = DesignTask(**data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update(self, task: DesignTask, data: dict) -> DesignTask:
        for key, value in data.items():
            if value is not None:
                setattr(task, key, value)
        await self.db.flush()
        return task


class ProductionTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: UUID) -> ProductionTask | None:
        result = await self.db.execute(select(ProductionTask).where(ProductionTask.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks(self, skip: int = 0, limit: int = 20, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list[ProductionTask], int]:
        q = select(ProductionTask)
        if status:
            q = q.where(ProductionTask.status == status)
        if order_id:
            q = q.where(ProductionTask.order_id == UUID(order_id))
        if assigned_to:
            q = q.where(ProductionTask.assigned_to == UUID(assigned_to))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(ProductionTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> ProductionTask:
        task = ProductionTask(**data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update(self, task: ProductionTask, data: dict) -> ProductionTask:
        for key, value in data.items():
            if value is not None:
                setattr(task, key, value)
        await self.db.flush()
        return task


class InstallationTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: UUID) -> InstallationTask | None:
        result = await self.db.execute(select(InstallationTask).where(InstallationTask.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks(self, skip: int = 0, limit: int = 20, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list[InstallationTask], int]:
        q = select(InstallationTask)
        if status:
            q = q.where(InstallationTask.status == status)
        if order_id:
            q = q.where(InstallationTask.order_id == UUID(order_id))
        if assigned_to:
            q = q.where(InstallationTask.assigned_to == UUID(assigned_to))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(InstallationTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> InstallationTask:
        task = InstallationTask(**data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update(self, task: InstallationTask, data: dict) -> InstallationTask:
        for key, value in data.items():
            if value is not None:
                setattr(task, key, value)
        await self.db.flush()
        return task


class AttachmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Attachment:
        att = Attachment(**data)
        self.db.add(att)
        await self.db.flush()
        return att

    async def get_by_task(self, related_type: str, related_id: UUID) -> list[Attachment]:
        result = await self.db.execute(
            select(Attachment)
            .where(Attachment.related_type == related_type, Attachment.related_id == related_id)
            .order_by(Attachment.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, attachment_id: UUID) -> bool:
        att = await self.db.get(Attachment, attachment_id)
        if not att:
            return False
        await self.db.delete(att)
        await self.db.flush()
        return True
