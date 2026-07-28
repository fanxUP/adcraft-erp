"""订单成本聚合：统一汇总外协、库存领用与手工成本。"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockRecord
from app.models.outsource import OutsourceTask
from app.models.project_cost import ProjectCost


@dataclass(frozen=True)
class OrderCostBreakdown:
    outsource: Decimal
    inventory: Decimal
    manual: Decimal

    @property
    def total(self) -> Decimal:
        return self.outsource + self.inventory + self.manual


class OrderCostAggregationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate(self, document_id: UUID) -> OrderCostBreakdown:
        outsource = await self._sum(
            select(func.coalesce(func.sum(OutsourceTask.total_amount), 0)).where(
                OutsourceTask.related_doc_id == document_id,
                OutsourceTask.status.in_(("completed", "settled")),
            )
        )
        inventory = await self._sum(
            select(func.coalesce(func.sum(StockRecord.total_cost), 0)).where(
                StockRecord.document_id == document_id,
                StockRecord.record_type == "out",
            )
        )
        manual = await self._sum(
            select(func.coalesce(func.sum(ProjectCost.amount), 0)).where(
                ProjectCost.document_id == document_id,
                ProjectCost.deleted_at.is_(None),
            )
        )
        return OrderCostBreakdown(
            outsource=outsource,
            inventory=inventory,
            manual=manual,
        )

    async def _sum(self, statement) -> Decimal:
        result = await self.db.execute(statement)
        return Decimal(str(result.scalar() or 0))
