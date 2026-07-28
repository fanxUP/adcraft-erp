"""验收与订单状态同步的回归测试。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.acceptance_service import AcceptanceService


@pytest.mark.asyncio
async def test_acceptance_sync_uses_authenticated_operator():
    db = MagicMock()
    form = MagicMock()
    form.id = uuid4()
    form.status = "pending"
    form.accepted_at = None
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
        acceptance_id=form.id,
    )


@pytest.mark.asyncio
async def test_acceptance_status_stays_pending_when_order_sync_fails():
    db = MagicMock()
    db.flush = AsyncMock()
    form = MagicMock()
    form.id = uuid4()
    form.status = "pending"
    form.accepted_at = None
    form.items = [MagicMock(item_status="accepted")]
    form.document = MagicMock(
        id=uuid4(),
        doc_type="order",
        status="pending_acceptance",
    )

    with patch(
        "app.services.acceptance_service.AcceptanceRepository"
    ) as repository_class, patch(
        "app.services.acceptance_service.BusinessDocumentService"
    ) as service_class:
        repository = repository_class.return_value
        repository.get_by_id = AsyncMock(return_value=form)
        service_class.return_value.change_status = AsyncMock(
            side_effect=ValueError("订单状态异常")
        )

        service = AcceptanceService(db)
        with pytest.raises(ValueError, match="订单状态同步失败"):
            await service.change_status(
                form.id,
                "accepted",
                operated_by=uuid4(),
                accepted_by="客户代表",
            )

    assert form.status == "pending"
    assert form.accepted_at is None


@pytest.mark.asyncio
async def test_acceptance_rejects_unfinished_items():
    db = MagicMock()
    form = MagicMock()
    form.id = uuid4()
    form.status = "pending"
    form.items = [
        MagicMock(item_name="门头", item_status="accepted"),
        MagicMock(item_name="灯箱", item_status="pending"),
    ]

    with patch(
        "app.services.acceptance_service.AcceptanceRepository"
    ) as repository_class:
        repository_class.return_value.get_by_id = AsyncMock(return_value=form)

        service = AcceptanceService(db)
        with pytest.raises(ValueError, match="仍有未确认的验收明细"):
            await service.change_status(
                form.id,
                "accepted",
                operated_by=uuid4(),
            )
