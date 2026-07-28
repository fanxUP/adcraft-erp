"""订单成本聚合服务测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.order_cost_service import OrderCostAggregationService


@pytest.mark.asyncio
async def test_cost_breakdown_aggregates_all_supported_sources():
    db = MagicMock()
    results = []
    for value in (Decimal("1200.50"), Decimal("300.25"), Decimal("99.25")):
        result = MagicMock()
        result.scalar.return_value = value
        results.append(result)
    db.execute = AsyncMock(side_effect=results)

    breakdown = await OrderCostAggregationService(db).calculate(uuid4())

    assert breakdown.outsource == Decimal("1200.50")
    assert breakdown.inventory == Decimal("300.25")
    assert breakdown.manual == Decimal("99.25")
    assert breakdown.total == Decimal("1600.00")
