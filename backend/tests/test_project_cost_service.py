from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.payment import DebtSettleCreate, ExpenseUpdate
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
