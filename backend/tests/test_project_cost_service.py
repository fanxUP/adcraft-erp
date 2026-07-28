from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.project_cost_service import ProjectCostService


@pytest.mark.asyncio
async def test_sync_document_cost_uses_unified_order_service():
    document_id = uuid4()
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "order"
    db.execute = AsyncMock(return_value=result)

    with patch(
        "app.services.business_document_service.BusinessDocumentService"
    ) as service_class:
        order_service = service_class.return_value
        order_service.auto_calculate_cost = AsyncMock()

        await ProjectCostService(db)._sync_document_cost(document_id)

    service_class.assert_called_once_with(db, doc_type="order")
    order_service.auto_calculate_cost.assert_awaited_once_with(document_id)


@pytest.mark.asyncio
async def test_sync_document_cost_skips_quotes():
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "quote"
    db.execute = AsyncMock(return_value=result)

    with patch(
        "app.services.business_document_service.BusinessDocumentService"
    ) as service_class:
        await ProjectCostService(db)._sync_document_cost(uuid4())

    service_class.assert_not_called()
