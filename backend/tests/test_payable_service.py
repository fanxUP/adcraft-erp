"""应付台账的金额与状态规则测试。"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.payable_service import (
    PayableService,
    calculate_payable_status,
    validate_payable_amount,
)


@pytest.mark.parametrize(
    ("total", "paid", "status"),
    [
        ("100.00", "0", "unpaid"),
        ("100.00", "25", "partial"),
        ("100.00", "100", "paid"),
        ("100.00", "125", "paid"),
    ],
)
def test_calculate_payable_status(total, paid, status):
    assert calculate_payable_status(Decimal(total), Decimal(paid)) == status


def test_validate_payable_amount_accepts_zero_and_partial_amount():
    assert validate_payable_amount(Decimal("100.00"), Decimal("0")) == Decimal("0.00")
    assert validate_payable_amount(Decimal("100.00"), Decimal("40")) == Decimal("40.00")


@pytest.mark.parametrize("payable", ["-0.01", "100.01"])
def test_validate_payable_amount_rejects_out_of_range(payable):
    with pytest.raises(ValueError, match="待付款金额不能大于支出总额且不能小于0"):
        validate_payable_amount(Decimal("100.00"), Decimal(payable))


def test_calculate_payable_status_rejects_negative_paid_amount():
    with pytest.raises(ValueError, match="已付款金额不能小于0"):
        calculate_payable_status(Decimal("100.00"), Decimal("-1"))


@pytest.mark.asyncio
async def test_list_payables_calculates_partial_balance_from_payment_ledger():
    source_id = uuid4()
    expense = SimpleNamespace(
        id=source_id,
        expense_no="EXP20260916-0001",
        amount=Decimal("100.00"),
        payable_amount=Decimal("80.00"),
        payee_name="供应商甲",
        category="材料采购",
        description="测试支出",
        expense_date=None,
        created_at=None,
    )
    service = PayableService(MagicMock())
    service._load_sources = AsyncMock(return_value=[("expense", expense)])
    service._payment_summary = AsyncMock(
        return_value={("expense", source_id): (Decimal("30.00"), 1)}
    )

    rows, total = await service.list_payables(1, 20)

    assert total == 1
    assert rows[0]["status"] == "partial"
    assert rows[0]["payable_total_amount"] == 80.0
    assert rows[0]["paid_amount"] == 30.0
    assert rows[0]["remaining_amount"] == 50.0
    assert rows[0]["source_label"] == "经营支出"


def test_project_cost_payload_keeps_legacy_settled_rows_as_paid():
    source = SimpleNamespace(
        id=uuid4(),
        cost_no="260916-001",
        amount=Decimal("200.00"),
        debt_amount=Decimal("120.00"),
        is_settled=True,
        settled_at=None,
        payment_method="转账支付",
        payee_company_name="供应商乙",
        category="外协加工",
        description=None,
        remark=None,
        cost_date=None,
        created_at=None,
        document=None,
        document_item=None,
        customer=None,
    )

    row = PayableService._source_payload(
        "project_cost", source, Decimal("0"), 0
    )

    assert row["status"] == "paid"
    assert row["paid_amount"] == 120.0
    assert row["remaining_amount"] == 0.0


@pytest.mark.asyncio
async def test_void_active_payments_for_source_preserves_payment_facts():
    source_id = uuid4()
    payments = [
        SimpleNamespace(
            id=uuid4(), amount=Decimal("600.00"), is_voided=False,
            void_reason=None, voided_at=None,
        ),
        SimpleNamespace(
            id=uuid4(), amount=Decimal("400.00"), is_voided=False,
            void_reason=None, voided_at=None,
        ),
    ]
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = payments
    db.execute.return_value = result

    service = PayableService(db)
    service._load_source = AsyncMock(return_value=SimpleNamespace(id=source_id))

    summary = await service.void_active_payments_for_source(
        "expense",
        source_id,
        "随支出删除自动撤销；用户已确认",
        expected_payment_count=2,
        expected_paid_amount=Decimal("1000.00"),
    )

    assert summary["payment_count"] == 2
    assert summary["paid_amount"] == 1000.0
    assert summary["payment_ids"] == [str(payment.id) for payment in payments]
    assert all(payment.is_voided for payment in payments)
    assert all(payment.void_reason == "随支出删除自动撤销；用户已确认" for payment in payments)
    assert all(isinstance(payment.voided_at, datetime) for payment in payments)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_void_active_payments_rejects_stale_confirmation_snapshot():
    source_id = uuid4()
    payment = SimpleNamespace(
        id=uuid4(), amount=Decimal("1000.00"), is_voided=False,
        void_reason=None, voided_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [payment]
    db.execute.return_value = result

    service = PayableService(db)
    service._load_source = AsyncMock(return_value=SimpleNamespace(id=source_id))

    with pytest.raises(ValueError, match="付款情况已发生变化"):
        await service.void_active_payments_for_source(
            "expense",
            source_id,
            "随支出删除自动撤销；用户已确认",
            expected_payment_count=2,
            expected_paid_amount=Decimal("2000.00"),
        )

    assert payment.is_voided is False
    db.flush.assert_not_awaited()
