"""Repository for AI Provider CRUD operations."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider import AIProvider
from app.models.ai_model import AIModel


class AIProviderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, provider_id: UUID) -> AIProvider | None:
        result = await self.db.execute(
            select(AIProvider).where(AIProvider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> AIProvider | None:
        result = await self.db.execute(
            select(AIProvider).where(AIProvider.provider_code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, skip: int = 0, limit: int = 50, enabled_only: bool = False
    ) -> tuple[list[AIProvider], int]:
        q = select(AIProvider)
        count_q = select(func.count(AIProvider.id))
        if enabled_only:
            q = q.where(AIProvider.enabled.is_(True))
            count_q = count_q.where(AIProvider.enabled.is_(True))

        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(AIProvider.priority, AIProvider.created_at.desc())
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        return items, total

    async def create(self, data: dict) -> AIProvider:
        provider = AIProvider(**data)
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def update(self, provider_id: UUID, data: dict) -> AIProvider | None:
        stmt = (
            sa_update(AIProvider)
            .where(AIProvider.id == provider_id)
            .values(**data)
            .returning(AIProvider)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def delete(self, provider_id: UUID) -> bool:
        provider = await self.get_by_id(provider_id)
        if not provider:
            return False
        await self.db.delete(provider)
        await self.db.flush()
        return True

    async def set_health(
        self, provider_id: UUID, status: str, score: float | None = None
    ) -> None:
        values = {"health_status": status, "last_health_check_at": datetime.now(timezone.utc)}
        if score is not None:
            values["health_score"] = score
        stmt = sa_update(AIProvider).where(AIProvider.id == provider_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()
