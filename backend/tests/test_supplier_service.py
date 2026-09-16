"""统一供应商主数据的纯业务规则测试。"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.services.supplier_service import (
    SupplierService,
    _summarize_ledger_sources,
    normalize_supplier_type,
)


def test_supplier_type_is_normalized_and_validated():
    assert normalize_supplier_type("  material ") == "material"

    with pytest.raises(ValueError, match="供应商类型不受支持"):
        normalize_supplier_type("unknown")


def test_supplier_serialization_hides_bank_fields_by_default():
    supplier = SimpleNamespace(
        id="supplier-id",
        vendor_no="V260916-001",
        name="供应商甲",
        short_name="甲供应",
        supplier_type="material",
        contact_person="张三",
        phone="13800000000",
        email="supplier@example.com",
        address="乌鲁木齐",
        tax_id="91320000000000000A",
        bank_name="某银行",
        bank_account="6222000000000000",
        service_type=None,
        coop_rating=None,
        settlement_method="月结",
        settlement_days=30,
        tax_rate=None,
        remark=None,
        is_active=True,
        created_at=datetime(2026, 9, 16, 8, 0, 0),
    )

    payload = SupplierService.serialize_supplier(supplier)

    assert payload["name"] == "供应商甲"
    assert payload["supplier_type"] == "material"
    assert payload["bank_name"] is None
    assert payload["bank_account"] is None

    privileged = SupplierService.serialize_supplier(supplier, include_bank=True)
    assert privileged["bank_account"] == "6222000000000000"


def test_supplier_bank_write_requires_explicit_permission():
    service = SupplierService(None, viewer=SimpleNamespace(permissions=[]))

    with pytest.raises(ValueError, match="没有修改供应商收款账户的权限"):
        service._assert_bank_write_allowed({"bank_account": "6222"})

    privileged = SupplierService(
        None,
        viewer=SimpleNamespace(
            roles=[SimpleNamespace(permissions=[
                SimpleNamespace(code="supplier_center:read"),
                SimpleNamespace(code="supplier:read"),
                SimpleNamespace(code="supplier:bank:view"),
                SimpleNamespace(code="supplier:bank:edit"),
            ])],
        ),
    )
    privileged._assert_bank_write_allowed({"bank_account": "6222"})


def test_supplier_stats_use_the_same_paid_and_remaining_ledger_totals():
    source_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    expense = SimpleNamespace(
        id=source_id,
        amount=Decimal("3000.00"),
        payable_amount=Decimal("2000.00"),
    )

    stats = _summarize_ledger_sources(
        "expense",
        [expense],
        {("expense", source_id): (Decimal("1500.00"), 2)},
    )

    assert stats == {
        "count": 1,
        "amount": Decimal("3000.00"),
        "payable": Decimal("2000.00"),
        "initial_paid": Decimal("1000.00"),
        "paid": Decimal("2500.00"),
        "remaining": Decimal("500.00"),
    }


@pytest.mark.asyncio
async def test_supplier_detail_stats_read_payable_payments_for_expenses():
    supplier_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    expense_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    expense = SimpleNamespace(
        id=expense_id,
        amount=Decimal("3000.00"),
        payable_amount=Decimal("2000.00"),
    )

    class FakeResult:
        def __init__(self, rows=None, one_value=None):
            self.rows = rows or []
            self.one_value = one_value

        def scalars(self):
            return self

        def all(self):
            return self.rows

        def one(self):
            return self.one_value

    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                FakeResult(rows=[]),
                FakeResult(rows=[expense]),
                FakeResult(rows=[("expense", expense_id, Decimal("1500.00"), 2)]),
                FakeResult(one_value=(0, Decimal("0"), Decimal("0"))),
            ]
        )
    )

    stats = await SupplierService(db)._stats(supplier_id)

    assert stats["expense_count"] == 1
    assert stats["expense_amount"] == 3000.0
    assert stats["expense_payable"] == 2000.0
    assert stats["expense_paid"] == 2500.0
    assert stats["expense_remaining"] == 500.0
    assert db.execute.await_count == 4
