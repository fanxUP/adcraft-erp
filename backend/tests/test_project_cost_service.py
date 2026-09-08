from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.payment import DebtSettleCreate, ExpenseUpdate, ProjectCostUpdate
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


def test_debt_settlement_amount_must_be_positive():
    with pytest.raises(ValueError, match="结清金额必须大于0"):
        DebtSettleCreate(settle_amount=0)


def test_expense_update_amount_must_be_positive():
    with pytest.raises(ValueError, match="支出金额必须大于0"):
        ExpenseUpdate(amount=-1)


@pytest.mark.asyncio
async def test_settle_debt_requires_full_outstanding_amount():
    cost = MagicMock()
    cost.is_debt = True
    cost.is_settled = False
    cost.debt_amount = 500

    service = ProjectCostService(MagicMock())
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=cost)

    cost_id = uuid4()
    with pytest.raises(ValueError, match="结清金额必须等于欠款金额"):
        await service.settle_debt(
            cost_id,
            {"settle_amount": 100, "payment_method": "转账支付"},
        )

    assert cost.is_settled is False
    service.repo.get_by_id.assert_awaited_once_with(cost_id, for_update=True)


@pytest.mark.asyncio
async def test_settle_debt_does_not_duplicate_project_cost():
    cost = MagicMock()
    cost.id = uuid4()
    cost.cost_no = "COST-001"
    cost.document_id = uuid4()
    cost.document_item_id = None
    cost.customer_id = uuid4()
    cost.category = "材料费"
    cost.amount = 1000
    cost.debt_amount = 500
    cost.is_debt = True
    cost.is_settled = False
    cost.payment_method = None
    cost.remark = None
    cost.settled_at = None
    cost.description = "测试成本"
    cost.summary = None
    cost.cost_date = None
    cost.receipt_url = None
    cost.quantity = None
    cost.specification = None
    cost.unit = None
    cost.unit_price = None
    cost.payee_company_name = None
    cost.created_by = uuid4()
    cost.created_at = None
    cost.document = None
    cost.document_item = None
    cost.customer = None

    db = MagicMock()
    db.flush = AsyncMock()
    service = ProjectCostService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=cost)
    service.repo.create = AsyncMock()
    service._to_dict = MagicMock(
        side_effect=lambda item: {
            "is_settled": item.is_settled,
            "amount": float(item.amount),
        }
    )

    result = await service.settle_debt(
        cost.id,
        {"settle_amount": 500, "payment_method": "转账支付", "remark": "已付款"},
    )

    assert result["is_settled"] is True
    assert result["amount"] == 1000
    service.repo.create.assert_not_awaited()


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _order_doc(document_id):
    document = MagicMock()
    document.id = document_id
    document.doc_type = "order"
    document.customer_id = uuid4()
    document.project_name = "测试订单"
    document.doc_no = "O-TEST"
    return document


def _cost_payload(order_id, item_id=None):
    return {
        "order_id": str(order_id),
        "category": "材料费",
        "amount": 100,
        "order_item_id": str(item_id) if item_id else None,
    }


@pytest.mark.asyncio
async def test_create_cost_rejects_item_from_another_order():
    order_id = uuid4()
    item_id = uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_result(_order_doc(order_id)), _scalar_result(None)]
    )
    service = ProjectCostService(db)
    service.repo.create = AsyncMock()

    with patch(
        "app.services.project_cost_service.generate_project_cost_no",
        new=AsyncMock(return_value="COST-TEST-001"),
    ):
        with pytest.raises(ValueError, match="不属于当前业务单据"):
            await service.create_cost(
                _cost_payload(order_id, item_id), uuid4(), skip_sync=True
            )

    service.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_cost_rejects_inactive_order_item():
    order_id = uuid4()
    item_id = uuid4()
    item = MagicMock()
    item.id = item_id
    item.document_id = order_id
    item.lifecycle_status = "voided"

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_result(_order_doc(order_id)), _scalar_result(item)]
    )
    service = ProjectCostService(db)
    service.repo.create = AsyncMock()

    with patch(
        "app.services.project_cost_service.generate_project_cost_no",
        new=AsyncMock(return_value="COST-TEST-002"),
    ):
        with pytest.raises(ValueError, match="当前有效明细"):
            await service.create_cost(
                _cost_payload(order_id, item_id), uuid4(), skip_sync=True
            )

    service.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_cost_requires_document_when_item_is_provided():
    item_id = uuid4()
    service = ProjectCostService(MagicMock())

    with pytest.raises(ValueError, match="必须关联订单或报价单"):
        await service.create_cost(
            _cost_payload(uuid4(), item_id) | {"order_id": None},
            uuid4(),
            skip_sync=True,
        )


@pytest.mark.asyncio
async def test_update_cost_can_explicitly_clear_item_association():
    cost = MagicMock()
    cost.id = uuid4()
    cost.document_id = uuid4()
    cost.document_item_id = uuid4()
    cost.document = _order_doc(cost.document_id)

    service = ProjectCostService(MagicMock())
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(side_effect=[cost, cost])
    service.repo.update = AsyncMock()
    service._sync_document_cost = AsyncMock()
    service._to_dict = MagicMock(return_value={"id": str(cost.id)})

    await service.update_cost(cost.id, {"order_item_id": None})

    service.repo.update.assert_awaited_once_with(
        cost,
        {"document_item_id": None},
        allow_null_fields={"document_item_id"},
    )


def test_project_cost_update_preserves_explicit_null_fields():
    payload = ProjectCostUpdate(order_item_id=None).model_dump(exclude_unset=True)

    assert payload == {"order_item_id": None}


@pytest.mark.asyncio
async def test_list_costs_passes_order_item_filter_to_repository():
    order_id = uuid4()
    item_id = uuid4()
    service = ProjectCostService(MagicMock())
    service.repo.list_costs = AsyncMock(return_value=([], 0))

    result, total = await service.list_costs(
        1,
        20,
        order_id=order_id,
        order_item_id=item_id,
    )

    assert result == []
    assert total == 0
    assert service.repo.list_costs.await_args.args == (
        0,
        20,
        order_id,
        None,
        None,
        None,
        None,
        None,
        item_id,
    )


@pytest.mark.asyncio
async def test_order_cost_summary_separates_order_and_item_scope():
    order_id = uuid4()
    item_id = uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(_order_doc(order_id)))
    service = ProjectCostService(db)
    service.repo.get_document_item_cost_summary = AsyncMock(
        return_value=[
            {"document_item_id": None, "amount": Decimal("20.00"), "record_count": 1},
            {"document_item_id": item_id, "amount": Decimal("80.00"), "record_count": 2},
        ]
    )

    summary = await service.get_order_cost_summary(order_id)

    assert summary == {
        "order_id": str(order_id),
        "total_registered": 100.0,
        "order_scope_registered": 20.0,
        "item_scope_registered": 80.0,
        "items": [
            {
                "order_item_id": str(item_id),
                "total_registered": 80.0,
                "record_count": 2,
            }
        ],
    }
