"""Regression tests for order response price redaction."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.permissions import (
    PERM_FINANCE_VIEW_COST,
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_ORDER_READ,
    PERM_ORDER_VIEW_PRICE,
)
from app.services.business_document_service import BusinessDocumentService


def make_viewer(*permission_codes: str):
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    role = SimpleNamespace(permissions=permissions)
    return SimpleNamespace(roles=[role])


def make_order():
    now = datetime.now(timezone.utc)
    item = SimpleNamespace(
        id="item-1",
        item_name="标识牌",
        product_id=None,
        material_id=None,
        process_id=None,
        length=None,
        length_unit=None,
        width=1,
        width_unit="m",
        height=2,
        height_unit="m",
        quantity=1,
        unit="块",
        use_area=True,
        quantity_mode="area",
        pieces=None,
        area=2,
        unit_price=120,
        process_fee=10,
        installation_fee=20,
        design_fee=30,
        transport_fee=40,
        other_fee=5,
        subtotal_amount=325,
        remark=None,
        image_url=None,
        sort_order=0,
        group_id=None,
        group_name=None,
        material_process="铝板 / UV",
        lifecycle_status="active",
    )
    return SimpleNamespace(
        id="order-1",
        doc_type="order",
        doc_no="O20260910-0001",
        customer_id="customer-1",
        customer_name="客户A",
        customer=None,
        project_name="项目A",
        sales_user_id=None,
        status="confirmed",
        department="设计部",
        contact_person=None,
        contact_phone=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
        total_amount=325,
        paid_amount=0,
        unpaid_amount=325,
        cost_amount=100,
        gross_profit=225,
        remark=None,
        source_quote_id=None,
        delivery_deadline=None,
        installation_address=None,
        groups=[],
        items=[item],
        status_logs=[],
        design_tasks=[],
        production_tasks=[],
        installation_tasks=[],
    )


@pytest.mark.asyncio
async def test_order_summary_and_detail_omit_prices_without_explicit_permissions():
    service = BusinessDocumentService(
        AsyncMock(),
        doc_type="order",
        viewer=make_viewer(),
    )
    order = make_order()

    summary = service._to_summary(order)
    detail = service._to_detail(order)

    assert "total_amount" not in summary
    assert "paid_amount" not in summary
    assert "unpaid_amount" not in summary
    assert "cost_amount" not in summary
    assert "gross_profit" not in summary
    assert "total_amount" not in detail
    assert "paid_amount" not in detail
    assert "cost_amount" not in detail
    assert "unit_price" not in detail["items"][0]
    assert "subtotal_amount" not in detail["items"][0]


@pytest.mark.asyncio
async def test_order_summary_and_detail_keep_only_granted_price_groups():
    service = BusinessDocumentService(
        AsyncMock(),
        doc_type="order",
        viewer=make_viewer(PERM_ORDER_READ, PERM_ORDER_VIEW_PRICE, PERM_ORDER_ITEM_VIEW_PRICE),
    )
    order = make_order()

    summary = service._to_summary(order)
    detail = service._to_detail(order)

    assert summary["total_amount"] == 325.0
    assert summary["paid_amount"] == 0.0
    assert summary["unpaid_amount"] == 325.0
    assert "cost_amount" not in summary
    assert detail["total_amount"] == 325.0
    assert detail["items"][0]["unit_price"] == 120.0
    assert detail["items"][0]["subtotal_amount"] == 325.0

    finance_service = BusinessDocumentService(
        AsyncMock(),
        doc_type="order",
        viewer=make_viewer(PERM_ORDER_READ, PERM_ORDER_VIEW_PRICE, PERM_FINANCE_VIEW_COST),
    )
    finance_summary = finance_service._to_summary(order)
    assert finance_summary["cost_amount"] == 100.0
    assert finance_summary["gross_profit"] == 225.0
