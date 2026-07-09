from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.project_cost import ProjectCost


class ProjectCostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, cost_id: UUID) -> ProjectCost | None:
        result = await self.db.execute(
            select(ProjectCost)
            .options(selectinload(ProjectCost.order), selectinload(ProjectCost.quote), selectinload(ProjectCost.customer))
            .where(ProjectCost.id == cost_id, ProjectCost.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_costs(
        self,
        skip: int = 0,
        limit: int = 20,
        order_id: UUID | None = None,
        quote_id: UUID | None = None,
        source_type: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[ProjectCost], int]:
        q = select(ProjectCost).options(
            selectinload(ProjectCost.order),
            selectinload(ProjectCost.quote),
            selectinload(ProjectCost.customer),
        ).where(ProjectCost.deleted_at.is_(None))
        if source_type:
            q = q.where(ProjectCost.source_type == source_type)
        if order_id:
            q = q.where(ProjectCost.order_id == order_id)
        if quote_id:
            q = q.where(ProjectCost.quote_id == quote_id)
        if category:
            q = q.where(ProjectCost.category == category)
        if date_from:
            q = q.where(ProjectCost.cost_date >= date_from)
        if date_to:
            q = q.where(ProjectCost.cost_date <= date_to)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(ProjectCost.cost_date.desc(), ProjectCost.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, cost: ProjectCost) -> ProjectCost:
        self.db.add(cost)
        await self.db.flush()
        return cost

    async def update(self, cost: ProjectCost, data: dict) -> ProjectCost:
        for k, v in data.items():
            if v is not None:
                setattr(cost, k, v)
        await self.db.flush()
        return cost

    async def soft_delete(self, cost: ProjectCost) -> ProjectCost:
        cost.deleted_at = datetime.now()
        await self.db.flush()
        return cost

    async def get_order_cost_sum(self, order_id: UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(ProjectCost.amount), 0))
            .where(ProjectCost.order_id == order_id, ProjectCost.deleted_at.is_(None))
        )
        return Decimal(str(result.scalar()))

    async def get_costs_summary(self, order_ids: list[UUID]) -> dict[str, float]:
        """Return {order_id: total_cost} for a batch of orders."""
        if not order_ids:
            return {}
        result = await self.db.execute(
            select(ProjectCost.order_id, func.coalesce(func.sum(ProjectCost.amount), 0))
            .where(
                ProjectCost.order_id.in_(order_ids),
                ProjectCost.deleted_at.is_(None),
            )
            .group_by(ProjectCost.order_id)
        )
        return {str(row[0]): float(row[1]) for row in result.all()}

    async def get_quote_costs_summary(self, quote_ids: list[UUID]) -> dict[str, float]:
        """Return {quote_id: total_cost} for a batch of quotes."""
        if not quote_ids:
            return {}
        result = await self.db.execute(
            select(ProjectCost.quote_id, func.coalesce(func.sum(ProjectCost.amount), 0))
            .where(
                ProjectCost.quote_id.in_(quote_ids),
                ProjectCost.deleted_at.is_(None),
                ProjectCost.source_type == "quote",
            )
            .group_by(ProjectCost.quote_id)
        )
        return {str(row[0]): float(row[1]) for row in result.all()}
