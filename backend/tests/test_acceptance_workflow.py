"""验收与订单状态同步的回归测试。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.acceptance_service import AcceptanceService


@pytest.mark.asyncio
async def test_acceptance_sync_uses_authenticated_operator():
    db = MagicMock()
    form = MagicMock()
    form.document = MagicMock(
        id=uuid4(),
        doc_type="order",
        status="pending_acceptance",
    )
    operator_id = uuid4()

    with patch(
        "app.services.acceptance_service.BusinessDocumentService"
    ) as service_class:
        order_service = service_class.return_value
        order_service.change_status = AsyncMock()

        service = AcceptanceService(db)
        await service._sync_order_on_acceptance(
            form,
            "completed",
            operated_by=operator_id,
        )

    order_service.change_status.assert_awaited_once_with(
        form.document.id,
        "completed",
        reason="验收单自动触发",
        operated_by=operator_id,
    )
