"""Regression tests for task-facing order price visibility."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.permissions import (
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_ORDER_READ,
    PERM_ORDER_VIEW_PRICE,
)
from app.schemas.order import OrderItemResponse
from app.services.task_service import (
    _enrich_task_order,
    _task_order_item_option_map,
)


ORDER_ID = UUID("33333333-3333-3333-3333-333333333333")
ITEM_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TASK_ID = UUID("99999999-9999-9999-9999-999999999999")


def _viewer(*permission_codes: str):
    codes = list(permission_codes)
    if any(code in {PERM_ORDER_VIEW_PRICE, PERM_ORDER_ITEM_VIEW_PRICE} for code in codes):
        if PERM_ORDER_READ not in codes:
            codes.insert(0, PERM_ORDER_READ)
    return SimpleNamespace(
        roles=[
            SimpleNamespace(
                name="viewer",
                permissions=[SimpleNamespace(code=code) for code in codes],
            )
        ]
    )


def _order_item() -> OrderItemResponse:
    return OrderItemResponse(
        id=str(ITEM_ID),
        item_name="标识牌",
        quantity=3,
        unit_price=120,
        process_fee=15,
        installation_fee=20,
        design_fee=5,
        transport_fee=8,
        other_fee=2,
        subtotal_amount=410,
    )


@pytest.mark.asyncio
async def test_task_order_enrichment_omits_order_total_without_permission():
    db = AsyncMock()
    query_result = MagicMock()
    query_result.fetchone.return_value = (
        "O20260910-0001",
        "示例客户",
        "设计部",
        "王老师",
        "13800138000",
    )
    db.execute = AsyncMock(return_value=query_result)
    payload = {
        "document_id": str(ORDER_ID),
        "total_amount": 12345.67,
    }

    result = await _enrich_task_order(db, payload, viewer=_viewer())

    assert "total_amount" not in result
    assert result["order_no"] == "O20260910-0001"
    assert result["contact_name"] == "王老师"
    assert result["contact_phone"] == "13800138000"
    assert "total_amount" not in str(db.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_task_order_enrichment_uses_related_customer_when_snapshot_is_empty():
    db = AsyncMock()
    query_result = MagicMock()
    query_result.fetchone.return_value = (
        "O20260910-0001",
        "新疆知味居经营管理有限公司",
        "第二十六中学",
        "王老师",
        "13800138000",
    )
    db.execute = AsyncMock(return_value=query_result)
    payload = {"document_id": str(ORDER_ID)}

    result = await _enrich_task_order(db, payload, viewer=_viewer())

    query = str(db.execute.await_args.args[0])
    assert "LEFT JOIN customers" in query
    assert "COALESCE" in query
    assert result["customer_name"] == "新疆知味居经营管理有限公司"


@pytest.mark.asyncio
async def test_task_order_enrichment_keeps_order_total_for_explicit_permission():
    db = AsyncMock()
    query_result = MagicMock()
    query_result.fetchone.return_value = (
        "O20260910-0001",
        "示例客户",
        "财务部",
        "李经理",
        "13900139000",
        12345.67,
    )
    db.execute = AsyncMock(return_value=query_result)
    payload = {"document_id": str(ORDER_ID)}

    result = await _enrich_task_order(
        db,
        payload,
        viewer=_viewer(PERM_ORDER_VIEW_PRICE),
    )

    assert result["total_amount"] == 12345.67
    assert result["contact_name"] == "李经理"
    assert result["contact_phone"] == "13900139000"
    assert "total_amount" in str(db.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_task_order_item_options_omit_all_line_prices_without_permission():
    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            doc_type="order",
            deleted_at=None,
            status="in_production",
        )
    )
    item_result = MagicMock()
    item_result.scalars.return_value.all.return_value = [_order_item()]
    db.execute = AsyncMock(return_value=item_result)

    with (
        patch("app.services.task_service._task_stage_states_by_item", new=AsyncMock(return_value=({}, {}))),
        patch("app.services.task_service._task_order_item_link_rows", new=AsyncMock(return_value=[])),
        patch("app.services.task_service._blocking_outsource_map", new=AsyncMock(return_value={})),
    ):
        options = await _task_order_item_option_map(
            db,
            ORDER_ID,
            "production",
            task_id=TASK_ID,
            viewer=_viewer(),
        )

    option = options[ITEM_ID]
    for field in (
        "unit_price",
        "process_fee",
        "installation_fee",
        "design_fee",
        "transport_fee",
        "other_fee",
        "subtotal_amount",
    ):
        assert field not in option


@pytest.mark.asyncio
async def test_task_order_item_options_keep_line_prices_for_explicit_permission():
    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            doc_type="order",
            deleted_at=None,
            status="in_production",
        )
    )
    item_result = MagicMock()
    item_result.scalars.return_value.all.return_value = [_order_item()]
    db.execute = AsyncMock(return_value=item_result)

    with (
        patch("app.services.task_service._task_stage_states_by_item", new=AsyncMock(return_value=({}, {}))),
        patch("app.services.task_service._task_order_item_link_rows", new=AsyncMock(return_value=[])),
        patch("app.services.task_service._blocking_outsource_map", new=AsyncMock(return_value={})),
    ):
        options = await _task_order_item_option_map(
            db,
            ORDER_ID,
            "production",
            task_id=TASK_ID,
            viewer=_viewer(PERM_ORDER_ITEM_VIEW_PRICE),
        )

    option = options[ITEM_ID]
    assert option["unit_price"] == 120
    assert option["subtotal_amount"] == 410
