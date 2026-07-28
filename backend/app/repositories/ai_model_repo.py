"""Repository for AI Model CRUD operations."""
from uuid import UUID

from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model import AIModel


class AIModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, model_id: UUID) -> AIModel | None:
        result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def list_by_provider(
        self, provider_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[AIModel], int]:
        q = select(AIModel).where(AIModel.provider_id == provider_id)
        count_q = select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)

        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(AIModel.priority, AIModel.created_at.desc())
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        return items, total

    async def list_all(
        self, skip: int = 0, limit: int = 100, enabled_only: bool = False
    ) -> tuple[list[AIModel], int]:
        q = select(AIModel)
        count_q = select(func.count(AIModel.id))
        if enabled_only:
            q = q.where(AIModel.enabled.is_(True))
            count_q = count_q.where(AIModel.enabled.is_(True))

        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(AIModel.priority, AIModel.created_at.desc())
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        return items, total

    async def create(self, data: dict) -> AIModel:
        model = AIModel(**data)
        self.db.add(model)
        await self.db.flush()
        return model

    async def update(self, model_id: UUID, data: dict) -> AIModel | None:
        """Update model using direct UPDATE statement to avoid greenlet issues."""
        stmt = (
            sa_update(AIModel)
            .where(AIModel.id == model_id)
            .values(**data)
            .returning(AIModel)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def delete(self, model_id: UUID) -> bool:
        model = await self.get_by_id(model_id)
        if not model:
            return False
        await self.db.delete(model)
        await self.db.flush()
        return True
