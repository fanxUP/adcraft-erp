"""Repository for AI Task Route operations."""
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ai_task_route import AITaskRoute


class AITaskRouteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, route_id: UUID) -> Optional[AITaskRoute]:
        result = await self.db.execute(
            select(AITaskRoute).where(AITaskRoute.id == route_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_id: UUID, task_code: str) -> Optional[AITaskRoute]:
        result = await self.db.execute(
            select(AITaskRoute).where(
                AITaskRoute.tenant_id == tenant_id,
                AITaskRoute.task_code == task_code,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        enabled_only: bool = False,
        search: Optional[str] = None,
    ) -> tuple[list[AITaskRoute], int]:
        query = select(AITaskRoute).where(AITaskRoute.tenant_id == tenant_id)

        if enabled_only:
            query = query.where(AITaskRoute.enabled.is_(True))
        if search:
            query = query.where(
                AITaskRoute.task_code.ilike(f"%{search}%")
                | AITaskRoute.task_name.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AITaskRoute.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(
        self, tenant_id: UUID, data: dict, created_by: Optional[UUID] = None
    ) -> AITaskRoute:
        route = AITaskRoute(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_by=created_by or tenant_id,
            **data,
        )
        self.db.add(route)
        await self.db.flush()
        return route

    async def update(self, route_id: UUID, data: dict) -> Optional[AITaskRoute]:
        data["version"] = AITaskRoute.version + 1
        result = await self.db.execute(
            update(AITaskRoute)
            .where(AITaskRoute.id == route_id)
            .values(**data)
            .returning(AITaskRoute)
        )
        return result.scalar_one_or_none()

    async def delete(self, route_id: UUID) -> bool:
        result = await self.db.execute(
            delete(AITaskRoute).where(AITaskRoute.id == route_id)
        )
        return result.rowcount > 0

    async def list_by_task_codes(
        self, tenant_id: UUID, task_codes: list[str], enabled_only: bool = True
    ) -> list[AITaskRoute]:
        query = select(AITaskRoute).where(
            AITaskRoute.tenant_id == tenant_id,
            AITaskRoute.task_code.in_(task_codes),
        )
        if enabled_only:
            query = query.where(AITaskRoute.enabled.is_(True))
        result = await self.db.execute(query)
        return list(result.scalars().all())
