"""订单项目成本只读审计的纯规则测试。"""

from decimal import Decimal

from app.services.project_cost_audit_service import (
    build_financial_check,
    classify_cost_reference,
)


def _reference(**overrides):
    reference = {
        "record_id": "cost-1",
        "cost_no": "C-001",
        "document_id": "order-1",
        "document_exists": True,
        "document_type": "order",
        "item_id": "item-1",
        "item_exists": True,
        "item_document_id": "order-1",
        "item_lifecycle_status": "active",
        "lifecycle_status_available": True,
    }
    reference.update(overrides)
    return reference


def test_active_item_cost_reference_has_no_issue():
    assert classify_cost_reference(_reference()) == []


def test_cost_audit_distinguishes_orphan_and_cross_document_item():
    orphan = classify_cost_reference(_reference(item_exists=False, item_document_id=None))
    cross_document = classify_cost_reference(
        _reference(item_document_id="another-order")
    )

    assert orphan == ["item_missing"]
    assert cross_document == ["item_cross_document"]


def test_cost_audit_reports_missing_document_and_inactive_item():
    missing_document = classify_cost_reference(
        _reference(document_exists=False, document_type=None)
    )
    inactive_item = classify_cost_reference(
        _reference(item_lifecycle_status="voided")
    )

    assert missing_document == ["document_missing"]
    assert inactive_item == ["item_inactive"]


def test_cost_audit_does_not_guess_lifecycle_when_column_is_unavailable():
    reference = _reference(
        lifecycle_status_available=False,
        item_lifecycle_status=None,
    )

    assert classify_cost_reference(reference) == []


def test_financial_check_sums_each_source_once_and_calculates_profit():
    result = build_financial_check(
        {
            "total_amount": Decimal("1000.00"),
            "stored_cost": Decimal("350.00"),
            "stored_profit": Decimal("650.00"),
            "outsource_cost": Decimal("100.00"),
            "inventory_cost": Decimal("50.00"),
            "manual_cost": Decimal("200.00"),
        }
    )

    assert result["expected_cost"] == Decimal("350.00")
    assert result["expected_profit"] == Decimal("650.00")
    assert result["cost_matches"] is True
    assert result["profit_matches"] is True


def test_financial_check_flags_stored_total_or_profit_mismatch():
    result = build_financial_check(
        {
            "total_amount": Decimal("1000.00"),
            "stored_cost": Decimal("400.00"),
            "stored_profit": Decimal("600.00"),
            "outsource_cost": Decimal("100.00"),
            "inventory_cost": Decimal("50.00"),
            "manual_cost": Decimal("200.00"),
        }
    )

    assert result["cost_matches"] is False
    assert result["profit_matches"] is False
