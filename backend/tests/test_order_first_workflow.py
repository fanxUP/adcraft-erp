"""Unified order workflow: server calculations, lifecycle and API boundaries."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderCreate, OrderFundMutation
from app.services.business_document_service import ORDER_ITEM_MUTABLE_STATUSES
from app.services.order_management_service import document_totals, settlement_values


def test_order_creation_requires_idempotency_date_and_valid_lines():
    request = OrderCreate(
        request_id=uuid4(), order_date=date(2026, 10, 26),
        header={"customer_name": "测试客户", "project_name": "直接下单", "discount_amount": 100},
        items=[{"item_name": "灯箱", "quantity": 10, "unit_price": 100}],
    )
    assert request.header.discount_amount == Decimal("100")
    with pytest.raises(ValidationError):
        OrderCreate(request_id=uuid4(), order_date=date.today(), header={"project_name": "空订单"}, items=[])


def test_discount_tax_and_settlement_share_one_calculation():
    result = document_totals([Decimal("1000")], discount_amount=100, tax_rate=6)
    assert result["total_amount"] == Decimal("954.00")
    assert result["tax_amount"] == Decimal("54.00")
    cancelled = document_totals([1000], discount_amount=100, settlement_adjustment=-900)
    assert cancelled["total_amount"] == Decimal("0.00")


def test_overpayment_is_explicit_without_rewriting_actual_receipts():
    result = settlement_values(7000, 8000, 2000)
    assert result == {"total_amount": 7000.0, "paid_amount": 8000.0, "unpaid_amount": 0.0,
                      "overpaid_amount": 1000.0, "cost_amount": 2000.0, "gross_profit": 5000.0}


def test_completed_orders_are_editable_but_cancelled_orders_require_restore():
    assert "completed" in ORDER_ITEM_MUTABLE_STATUSES
    assert "cancelled" not in ORDER_ITEM_MUTABLE_STATUSES


def test_decimal_precision_is_not_an_execution_change():
    from app.services.business_document_service import BusinessDocumentService
    assert BusinessDocumentService._order_edit_values_equal(Decimal("10.000"), Decimal("10.0"))
    assert BusinessDocumentService._order_edit_values_equal(Decimal("10.000"), 10.0)
    assert not BusinessDocumentService._order_edit_values_equal(Decimal("10.000"), 11)


def test_fund_mutation_uses_positive_amount_and_explicit_actual_date():
    with pytest.raises(ValidationError):
        OrderFundMutation(request_id=uuid4(), payment_id=uuid4(), operation="refund", amount=-10,
                          reason="不能伪造金额", paid_at=date.today())
    with pytest.raises(ValidationError):
        OrderFundMutation(request_id=uuid4(), payment_id=uuid4(), operation="refund", amount=10, reason="退款")
