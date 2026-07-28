"""Repository for AI Request logging and querying."""
import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, bindparam, cast, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_request import AIRequest
from app.models.ai_usage_daily import AIUsageDaily


class AIRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, request_id: UUID) -> Optional[AIRequest]:
        result = await self.db.execute(
            select(AIRequest).where(AIRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_request_id(self, request_id: str) -> Optional[AIRequest]:
        result = await self.db.execute(
            select(AIRequest).where(AIRequest.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> AIRequest:
        record = AIRequest(id=uuid.uuid4(), **data)
        self.db.add(record)
        await self.db.flush()
        return record

    async def update(self, request_id: UUID, data: dict) -> Optional[AIRequest]:
        result = await self.db.execute(
            update(AIRequest)
            .where(AIRequest.id == request_id)
            .values(**data)
            .returning(AIRequest)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        task_code: Optional[str] = None,
        status: Optional[str] = None,
        provider_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[list[AIRequest], int]:
        query = select(AIRequest).where(AIRequest.tenant_id == tenant_id)

        if task_code:
            query = query.where(AIRequest.task_code == task_code)
        if status:
            query = query.where(AIRequest.status == status)
        if provider_id:
            query = query.where(AIRequest.provider_id == provider_id)
        if start_date:
            query = query.where(AIRequest.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(AIRequest.created_at < datetime.combine(end_date, datetime.min.time()).replace(day=end_date.day + 1))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AIRequest.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def upsert_usage_daily(
        self,
        tenant_id: UUID,
        usage_date: date,
        *,
        provider_id: Optional[UUID] = None,
        model_id: Optional[UUID] = None,
        task_code: Optional[str] = None,
        input_tokens_delta: int = 0,
        cached_input_tokens_delta: int = 0,
        output_tokens_delta: int = 0,
        cost_delta: float = 0.0,
        latency_ms: Optional[int] = None,
        success: bool = True,
    ) -> None:
        """Upsert daily usage aggregation record."""
        stmt = pg_insert(AIUsageDaily).values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usage_date=usage_date,
            provider_id=provider_id,
            model_id=model_id,
            task_code=task_code,
            request_count=1,
            success_count=1 if success else 0,
            failed_count=0 if success else 1,
            input_tokens=input_tokens_delta,
            cached_input_tokens=cached_input_tokens_delta,
            output_tokens=output_tokens_delta,
            estimated_cost=cost_delta,
            avg_latency_ms=latency_ms,
        )
        stmt = stmt.on_conflict_do_update(
            constraint=None,
            index_elements=[
                AIUsageDaily.tenant_id,
                AIUsageDaily.usage_date,
                AIUsageDaily.provider_id,
                AIUsageDaily.model_id,
                AIUsageDaily.task_code,
            ],
            set_=dict(
                request_count=AIUsageDaily.request_count + 1,
                success_count=AIUsageDaily.success_count + (1 if success else 0),
                failed_count=AIUsageDaily.failed_count + (0 if success else 1),
                input_tokens=AIUsageDaily.input_tokens + input_tokens_delta,
                cached_input_tokens=AIUsageDaily.cached_input_tokens + cached_input_tokens_delta,
                output_tokens=AIUsageDaily.output_tokens + output_tokens_delta,
                estimated_cost=AIUsageDaily.estimated_cost + cost_delta,
                avg_latency_ms=func.coalesce(
                    (AIUsageDaily.avg_latency_ms * AIUsageDaily.request_count + latency_ms) / (AIUsageDaily.request_count + 1),
                    latency_ms,
                ) if latency_ms else AIUsageDaily.avg_latency_ms,
            ),
        )
        # Need to handle the unique constraint properly — use raw SQL or ensure index exists
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        *,
        start_date: date,
        end_date: date,
        group_by: str = "day",
        task_code: Optional[str] = None,
    ) -> list[dict]:
        """Get aggregated usage summary."""
        query = select(AIUsageDaily).where(
            AIUsageDaily.tenant_id == tenant_id,
            AIUsageDaily.usage_date >= start_date,
            AIUsageDaily.usage_date <= end_date,
        )
        if task_code:
            query = query.where(AIUsageDaily.task_code == task_code)
        result = await self.db.execute(query)
        return list(result.scalars().all())
