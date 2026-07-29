"""验收与订单状态同步的回归测试。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.acceptance_service import AcceptanceService
from app.repositories.acceptance_repo import normalize_acceptance_item_data


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


@pytest.mark.asyncio
async def test_acceptance_rejects_quote_that_is_not_confirmed():
    db = MagicMock()
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = MagicMock(
        doc_type="quote",
        status="draft",
    )
    db.execute = AsyncMock(return_value=source_result)

    service = AcceptanceService(db)
    with pytest.raises(ValueError, match="尚未进入可验收阶段"):
        await service.create_acceptance({"quote_id": str(uuid4())})


@pytest.mark.asyncio
async def test_acceptance_rejects_duplicate_active_form():
    db = MagicMock()
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = MagicMock(
        doc_type="order",
        status="pending_acceptance",
    )
    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = uuid4()
    db.execute = AsyncMock(side_effect=[source_result, duplicate_result])

    service = AcceptanceService(db)
    with pytest.raises(ValueError, match="已有有效验收单"):
        await service.create_acceptance({"order_id": str(uuid4())})


@pytest.mark.asyncio
async def test_pending_acceptance_can_save_existing_item_results():
    db = MagicMock()
    db.flush = AsyncMock()
    item = MagicMock(
        id=uuid4(),
        item_name="原验收项目",
        item_status="pending",
        remark=None,
        image_url=None,
    )
    form = MagicMock(status="pending", items=[item])

    with patch(
        "app.services.acceptance_service.AcceptanceRepository"
    ) as repository_class:
        repository_class.return_value.get_by_id = AsyncMock(
            return_value=form
        )
        service = AcceptanceService(db)
        service._to_detail_dict = MagicMock(return_value={"status": "pending"})

        result = await service.update_acceptance(
            uuid4(),
            {
                "items": [
                    {
                        "id": str(item.id),
                        "item_name": "不允许在待验收阶段改名",
                        "item_status": "accepted",
                        "remark": "现场确认通过",
                    }
                ]
            },
        )

    assert result["status"] == "pending"
    assert item.item_name == "原验收项目"
    assert item.item_status == "accepted"
    assert item.remark == "现场确认通过"


def test_acceptance_item_alias_is_normalized_for_persistence():
    document_item_id = uuid4()

    normalized = normalize_acceptance_item_data(
        {
            "id": str(uuid4()),
            "order_item_id": str(document_item_id),
            "item_name": "灯箱",
            "item_status": "pending",
        }
    )

    assert normalized["document_item_id"] == document_item_id
    assert "order_item_id" not in normalized
    assert "id" not in normalized
