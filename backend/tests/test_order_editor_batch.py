"""订单报价式编辑器的整批预检/应用契约测试。"""

from decimal import Decimal
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.order import OrderEditRequest
from app.services.business_document_service import BusinessDocumentService

from tests.test_order_item_mutations import empty_relations, make_item, make_order


def test_order_edit_request_does_not_accept_client_calculated_totals():
    request = OrderEditRequest(
        reason="客户确认订单明细调整",
        expected_updated_at="2026-09-02T10:00:00",
        header={"project_name": "新门头项目", "remark": "保留原收款"},
        items=[
            {
                "id": str(uuid4()),
                "item_name": "灯箱字",
                "quantity": 2,
                "unit_price": 100,
                "other_fee": 10,
            }
        ],
        groups=[{"group_id": "group-a", "group_name": "门头", "sort_order": 0}],
    )

    assert request.header.project_name == "新门头项目"
    assert request.items[0].item_name == "灯箱字"
    assert not hasattr(request.items[0], "subtotal_amount")


@pytest.mark.asyncio
@pytest.mark.parametrize("route_name", ["preview", "apply"])
async def test_order_batch_routes_preserve_explicit_null_item_fields(route_name):
    """清空订单明细可空字段时，路由不能把显式 null 丢掉。"""
    import app.api.orders as orders_api

    request_data = OrderEditRequest(
        reason="清空订单明细备注",
        expected_updated_at="2026-09-09T10:00:00",
        header={"project_name": "测试订单"},
        items=[
            {
                "id": str(uuid4()),
                "item_name": "标志",
                "remark": None,
            }
        ],
    )
    service = MagicMock()
    service.preview_order_edit = AsyncMock(return_value={})
    service.apply_order_edit = AsyncMock(return_value={})
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), real_name="测试用户", username="tester")
    http_request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    with patch.object(orders_api, "BusinessDocumentService", return_value=service):
        if route_name == "preview":
            await orders_api.preview_order_edit(
                str(uuid4()), request_data, db, current_user
            )
            called = service.preview_order_edit.call_args.kwargs
        else:
            await orders_api.apply_order_edit(
                str(uuid4()), request_data, http_request, db, current_user
            )
            called = service.apply_order_edit.call_args.kwargs

    assert "remark" in called["items"][0]
    assert called["items"][0]["remark"] is None


@pytest.mark.asyncio
async def test_order_batch_preview_reports_item_diff_and_association_catalog_without_mutating():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    first = make_item()
    second = make_item(id=uuid4(), item_name="安装", sort_order=1, subtotal_amount=Decimal("80.00"))
    order = make_order(item=first, items=[first, second])
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[first, second])
    service.repo.get_groups = AsyncMock(return_value=[])
    service.repo.add_items = AsyncMock()
    service._collect_order_item_relations = AsyncMock(return_value=empty_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))

    result = await service.preview_order_edit(
        order.id,
        header={"project_name": "新项目"},
        items=[
            {
                "id": str(first.id),
                "item_name": first.item_name,
                "quantity": 2,
                "unit": first.unit,
                "unit_price": 100,
                "other_fee": 10,
                "group_id": "group-a",
                "group_name": "门头",
            },
            {
                "item_name": "运输",
                "quantity": 1,
                "unit": "项",
                "unit_price": 50,
                "other_fee": 0,
                "group_id": "group-b",
                "group_name": "运输",
            },
        ],
        groups=[
            {"group_id": "group-a", "group_name": "门头", "sort_order": 0},
            {"group_id": "group-b", "group_name": "运输", "sort_order": 1},
        ],
        expected_updated_at="2026-09-02T10:00:00",
        reason="客户确认订单明细调整",
    )

    assert result["can_apply"] is True
    assert result["after"]["total_amount"] == 260.0
    assert result["diff"]["added"] == 1
    assert result["diff"]["updated"] == 1
    assert result["diff"]["deleted"] == 1
    assert result["preview_id"]
    service.repo.add_items.assert_not_called()


@pytest.mark.asyncio
async def test_order_edit_treats_delivery_deadline_as_a_date_without_false_diff():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(
        item=item,
        items=[item],
        delivery_deadline=datetime(2026, 9, 2, 0, 0, 0),
    )
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    service.repo.get_groups = AsyncMock(return_value=[])
    service._collect_order_item_relations = AsyncMock(return_value=empty_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))

    result = await service.preview_order_edit(
        order.id,
        header={"delivery_deadline": "2026-09-02"},
        items=[{"id": str(item.id), "item_name": item.item_name}],
        groups=[],
        expected_updated_at="2026-09-02T10:00:00",
        reason="确认交付日期",
    )

    assert result["header_diff"] == []
    context = await service._build_order_edit_context(
        order,
        header={"delivery_deadline": "2026-09-02"},
        items_data=[{"id": str(item.id), "item_name": item.item_name}],
        groups_data=[],
    )
    assert context["header"]["delivery_deadline"] == datetime(2026, 9, 2, 0, 0, 0)


@pytest.mark.asyncio
async def test_order_batch_apply_preserves_existing_item_ids_and_soft_voids_missing_rows():
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    first = make_item()
    second = make_item(id=uuid4(), item_name="安装", sort_order=1, subtotal_amount=Decimal("80.00"))
    group = SimpleNamespace(
        id=uuid4(),
        group_id="group-a",
        group_name="门头",
        sort_order=0,
        created_at=datetime(2026, 9, 2, 9, 0, 0),
    )
    order = make_order(status="in_production", item=first, items=[first, second], groups=[group])
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[first, second])
    service.repo.get_groups = AsyncMock(return_value=[group])
    service.repo.get_item = AsyncMock(side_effect=lambda item_id, document_id=None: first if item_id == first.id else second)
    service.repo.get_next_version_no = AsyncMock(return_value=1)
    service.repo.create_version = AsyncMock()
    service._collect_order_item_relations = AsyncMock(return_value=empty_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))
    service._get_locked_order = AsyncMock(return_value=order)
    service._find_applied_mutation = AsyncMock(return_value=None)
    service._apply_order_item_refresh = AsyncMock(return_value={
        "status": "VERIFIED",
        "auto_refreshed": [],
        "preserved_facts": [],
        "pending_review": [],
        "adjustments": [],
        "blocked": [],
        "counts": {},
    })
    service._sync_framework_contract_projects = AsyncMock()
    service._sync_contact_to_customer = AsyncMock()

    items = [{
        "id": str(first.id),
        "item_name": first.item_name,
        "quantity": 2,
        "unit": first.unit,
        "unit_price": 100,
        "other_fee": 10,
        "group_id": "group-a",
        "group_name": "门头",
    }]
    operator = uuid4()
    preview = await service.preview_order_edit(
        order.id,
        header={"project_name": order.project_name},
        items=items,
        groups=[{"group_id": "group-a", "group_name": "门头", "sort_order": 0}],
        expected_updated_at="2026-09-02T10:00:00",
        reason="客户确认订单明细调整",
        operated_by=operator,
    )

    from unittest.mock import patch

    with patch("app.services.operation_log_service.log_operation", new_callable=AsyncMock):
        result = await service.apply_order_edit(
            order.id,
            header={"project_name": order.project_name},
            items=items,
            groups=[{"group_id": "group-a", "group_name": "门头", "sort_order": 0}],
            expected_updated_at="2026-09-02T10:00:00",
            reason="客户确认订单明细调整",
            operated_by=operator,
            preview_id=preview["preview_id"],
            plan_hash=preview["plan_hash"],
            preview_expires_at=preview["preview_expires_at"],
        )

    assert result["items"][0]["id"] == str(first.id)
    assert second.lifecycle_status == "voided"
    assert second.void_reason == "客户确认订单明细调整"
    service._apply_order_item_refresh.assert_awaited()
    db.delete.assert_not_called()
