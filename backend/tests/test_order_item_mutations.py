"""订单明细安全变更与回退报价功能下线测试。"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.order import OrderItemCreate, OrderItemMutationPreview
from app.models.task_order_item_link import TaskOrderItemLink
from app.services.business_document_service import (
    BusinessDocumentService,
    OrderDataMutationLocked,
    OrderItemMutationConflict,
)
from app.services.task_service import (
    TASK_ORDER_REVIEW_PREFIX,
    _apply_task_item_status_change,
    mark_tasks_for_order_review,
    task_order_review_required,
    task_order_review_reason,
)


def make_item(**overrides):
    values = {
        "id": uuid4(),
        "source_quote_item_id": None,
        "product_id": None,
        "material_id": None,
        "process_id": None,
        "item_name": "测试明细",
        "length": None,
        "length_unit": "m",
        "width": 2,
        "width_unit": "m",
        "height": 1,
        "height_unit": "m",
        "quantity": Decimal("1"),
        "unit": "套",
        "use_area": False,
        "quantity_mode": "piece",
        "pieces": Decimal("1"),
        "area": Decimal("2.00"),
        "unit_price": Decimal("100"),
        "process_fee": Decimal("0"),
        "installation_fee": Decimal("0"),
        "design_fee": Decimal("0"),
        "transport_fee": Decimal("0"),
        "other_fee": Decimal("0"),
        "subtotal_amount": Decimal("100.00"),
        "remark": None,
        "image_url": None,
        "sort_order": 0,
        "group_name": None,
        "group_id": None,
        "material_process": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_order(**overrides):
    item = overrides.pop("item", make_item())
    values = {
        "id": uuid4(),
        "doc_type": "order",
        "doc_no": "O-TEST-0001",
        "status": "pending_confirm",
        "updated_at": datetime(2026, 9, 2, 10, 0, 0),
        "created_at": datetime(2026, 9, 2, 9, 0, 0),
        "customer_id": uuid4(),
        "customer_name": "测试客户",
        "customer": None,
        "project_name": "测试项目",
        "sales_user_id": None,
        "total_amount": Decimal("100.00"),
        "paid_amount": Decimal("0.00"),
        "unpaid_amount": Decimal("100.00"),
        "cost_amount": Decimal("0.00"),
        "gross_profit": Decimal("100.00"),
        "remark": None,
        "department": None,
        "contact_person": None,
        "contact_phone": None,
        "delivery_deadline": None,
        "installation_address": None,
        "source_quote_id": None,
        "quote_mode": "regular",
        "subtotal_amount": Decimal("100.00"),
        "discount_amount": Decimal("0.00"),
        "tax_rate": Decimal("0.00"),
        "tax_amount": Decimal("0.00"),
        "valid_until": None,
        "quote_date": None,
        "items": [item],
        "groups": [],
        "status_logs": [],
        "design_tasks": [],
        "production_tasks": [],
        "installation_tasks": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def empty_relations():
    return {
        "payments": 0,
        "acceptance_forms": 0,
        "accepted_acceptance_forms": 0,
        "acceptance_item_refs": 0,
        "source_item_refs": 0,
        "tasks": {"design": 0, "production": 0, "installation": 0, "total": 0},
        "outsource_tasks": 0,
        "outsource_item_refs": 0,
        "project_costs": 0,
        "item_project_costs": 0,
        "stock_out_records": 0,
        "contract_links": 0,
        "framework_contract_links": 0,
        "vehicle_records": 0,
        "confirmed_statements": 0,
    }


def associated_relations():
    relations = empty_relations()
    relations["tasks"]["production"] = 1
    relations["tasks"]["total"] = 1
    relations["payments"] = 1
    relations["association_catalog"] = [
        {
            "module": "production_tasks",
            "label": "生产任务",
            "relation_type": "document",
            "record_id": str(uuid4()),
            "record_no": "P-TEST-0001",
            "status": "pending",
            "action": "refresh_or_review",
            "risk": "medium",
        },
        {
            "module": "payments",
            "label": "收款记录",
            "relation_type": "document",
            "record_id": str(uuid4()),
            "record_no": "PAY-TEST-0001",
            "status": "active",
            "action": "preserve_fact_and_reconcile",
            "risk": "high",
        },
    ]
    return relations


def test_order_item_lock_reasons_cover_execution_and_finance_links():
    order = make_order(status="completed")
    relations = empty_relations()
    relations["payments"] = 1
    relations["accepted_acceptance_forms"] = 1
    relations["tasks"]["total"] = 1
    relations["contract_links"] = 1

    reasons = BusinessDocumentService._order_item_lock_reasons(order, relations)
    codes = {reason["code"] for reason in reasons}

    assert {"STATUS_LOCKED", "PAYMENT_LINKED", "ACCEPTANCE_ACCEPTED", "TASK_LINKED", "CONTRACT_LINKED"} <= codes


def test_executing_associated_order_requires_confirmation_but_is_editable():
    order = make_order(status="in_production")

    decision = BusinessDocumentService._order_item_mutation_decision(
        order,
        associated_relations(),
        operation="update",
        after_total=Decimal("120.00"),
        paid_amount=Decimal("20.00"),
    )

    assert decision["decision"] == "APPROVAL_AND_ADJUSTMENT"
    assert decision["can_apply"] is True
    assert decision["requires_confirmation"] is True
    assert decision["requires_high_risk_ack"] is True
    assert not any(reason["code"] == "TASK_LINKED" for reason in decision["lock_reasons"])


def test_completed_order_remains_blocked_even_with_confirmation():
    order = make_order(status="completed")

    decision = BusinessDocumentService._order_item_mutation_decision(
        order,
        associated_relations(),
        operation="update",
        after_total=Decimal("120.00"),
        paid_amount=Decimal("20.00"),
    )

    assert decision["decision"] == "BLOCK"
    assert decision["can_apply"] is False
    assert any(reason["code"] == "STATUS_LOCKED" for reason in decision["lock_reasons"])


def test_deleting_order_item_always_requires_explicit_confirmation():
    """Deletion must show its impact even when no relation was detected."""
    order = make_order(status="pending_confirm")

    decision = BusinessDocumentService._order_item_mutation_decision(
        order,
        empty_relations(),
        operation="delete",
        after_total=Decimal("0.00"),
        paid_amount=Decimal("0.00"),
    )

    assert decision["decision"] == "CONFIRM_AND_REFRESH"
    assert decision["can_apply"] is True
    assert decision["requires_confirmation"] is True


def test_associated_edit_feature_flag_can_block_without_touching_data():
    order = make_order(status="in_production")

    with patch("app.services.business_document_service.settings.ORDER_ITEM_ASSOCIATED_EDIT_ENABLED", False):
        decision = BusinessDocumentService._order_item_mutation_decision(
            order,
            associated_relations(),
            operation="update",
            after_total=Decimal("120.00"),
            paid_amount=Decimal("20.00"),
        )

    assert decision["decision"] == "BLOCK"
    assert decision["can_apply"] is False
    assert any(
        reason["code"] == "ASSOCIATED_EDIT_FEATURE_DISABLED"
        for reason in decision["lock_reasons"]
    )


def test_expected_order_version_rejects_stale_client():
    order = make_order()

    with pytest.raises(OrderItemMutationConflict, match="其他人修改"):
        BusinessDocumentService._assert_expected_updated_at(
            order,
            "2026-09-02T10:00:01",
        )


@pytest.mark.asyncio
async def test_order_item_preview_recalculates_total_without_mutating():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(item=item)
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    service.repo.get_item = AsyncMock(return_value=item)
    service.repo.update_item = MagicMock()
    service._collect_order_item_relations = AsyncMock(return_value=empty_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))

    result = await service.preview_order_item_mutation(
        order.id,
        "update",
        item_id=item.id,
        data={"quantity": 2},
        expected_updated_at="2026-09-02T10:00:00",
    )

    assert result["can_apply"] is True
    assert result["before"]["total_amount"] == 100.0
    assert result["after"]["total_amount"] == 200.0
    assert result["delta"] == 100.0
    service.repo.update_item.assert_not_called()


@pytest.mark.asyncio
async def test_associated_preview_returns_confirmation_catalog_and_signed_batch():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(status="in_production", item=item)
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    service.repo.get_item = AsyncMock(return_value=item)
    service.repo.update_item = MagicMock()
    service._collect_order_item_relations = AsyncMock(return_value=associated_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("20"))

    result = await service.preview_order_item_mutation(
        order.id,
        "update",
        item_id=item.id,
        data={"quantity": 2},
        expected_updated_at="2026-09-02T10:00:00",
    )

    assert result["can_apply"] is True
    assert result["requires_confirmation"] is True
    assert result["decision"] == "APPROVAL_AND_ADJUSTMENT"
    assert result["preview_id"]
    assert result["plan_hash"]
    assert result["association_catalog"][0]["record_no"] == "P-TEST-0001"
    service.repo.update_item.assert_not_called()


@pytest.mark.asyncio
async def test_confirmed_associated_update_refreshes_and_records_pending_adjustment():
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(status="in_production", item=item)
    relations = associated_relations()
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    service.repo.get_item = AsyncMock(return_value=item)
    service.repo.get_next_version_no = AsyncMock(return_value=1)
    service.repo.create_version = AsyncMock()
    service._collect_order_item_relations = AsyncMock(return_value=relations)
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("20"))
    service._get_locked_order = AsyncMock(return_value=order)
    service._find_applied_mutation = AsyncMock(return_value=None)
    service._apply_order_item_refresh = AsyncMock(return_value={
        "status": "PENDING_ADJUSTMENT",
        "counts": {"auto_refreshed": 0, "preserved_facts": 1, "pending_review": 1, "adjustments": 1, "blocked": 0},
    })

    operator = uuid4()
    preview = await service.preview_order_item_mutation(
        order.id,
        "update",
        item_id=item.id,
        data={"quantity": 2},
        reason="客户确认变更数量",
        expected_updated_at="2026-09-02T10:00:00",
        operated_by=operator,
    )

    with pytest.raises(ValueError, match="影响目录"):
        await service.mutate_order_item(
            order.id,
            "update",
            item_id=item.id,
            data={"quantity": 2},
            reason="客户确认变更数量",
            expected_updated_at="2026-09-02T10:00:00",
            operated_by=uuid4(),
            preview_id=preview["preview_id"],
            plan_hash=preview["plan_hash"],
            preview_expires_at=preview["preview_expires_at"],
            confirm_high_risk=True,
        )

    with patch("app.services.operation_log_service.log_operation", new_callable=AsyncMock):
        result = await service.mutate_order_item(
            order.id,
            "update",
            item_id=item.id,
            data={"quantity": 2},
            reason="客户确认变更数量",
            expected_updated_at="2026-09-02T10:00:00",
            operated_by=operator,
            preview_id=preview["preview_id"],
            plan_hash=preview["plan_hash"],
            preview_expires_at=preview["preview_expires_at"],
            confirm_high_risk=True,
        )

    assert result["change_batch"]["status"] == "PENDING_ADJUSTMENT"
    assert item.quantity == Decimal("2")
    service._apply_order_item_refresh.assert_awaited_once()
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_confirmed_associated_delete_voids_item_instead_of_physical_delete():
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    other_item = make_item(item_name="第二条明细", subtotal_amount=Decimal("80.00"))
    order = make_order(status="designing", item=item, items=[item, other_item])
    relations = associated_relations()
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item, other_item])
    service.repo.get_item = AsyncMock(return_value=item)
    service.repo.get_next_version_no = AsyncMock(return_value=1)
    service.repo.create_version = AsyncMock()
    service._collect_order_item_relations = AsyncMock(return_value=relations)
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("20"))
    service._get_locked_order = AsyncMock(return_value=order)
    service._find_applied_mutation = AsyncMock(return_value=None)
    service._apply_order_item_refresh = AsyncMock(return_value={
        "status": "PENDING_ADJUSTMENT",
        "counts": {"auto_refreshed": 0, "preserved_facts": 1, "pending_review": 1, "adjustments": 1, "blocked": 0},
    })

    operator = uuid4()
    preview = await service.preview_order_item_mutation(
        order.id,
        "delete",
        item_id=item.id,
        data=None,
        reason="客户取消制作项",
        expected_updated_at="2026-09-02T10:00:00",
        operated_by=operator,
    )

    with patch("app.services.operation_log_service.log_operation", new_callable=AsyncMock):
        await service.mutate_order_item(
            order.id,
            "delete",
            item_id=item.id,
            reason="客户取消制作项",
            expected_updated_at="2026-09-02T10:00:00",
            operated_by=operator,
            preview_id=preview["preview_id"],
            plan_hash=preview["plan_hash"],
            preview_expires_at=preview["preview_expires_at"],
            confirm_high_risk=True,
        )

    assert item.lifecycle_status == "voided"
    assert item.void_reason == "客户取消制作项"
    assert item.voided_at is not None
    db.delete.assert_not_called()


def test_relation_actions_preserve_historical_facts():
    assert BusinessDocumentService._relation_action("payments", "active")["action"] == "preserve_fact_and_reconcile"
    assert BusinessDocumentService._relation_action("acceptance_forms", "accepted")["action"] == "preserve_fact_and_adjust"
    assert BusinessDocumentService._relation_action("outsource_tasks", "pending")["action"] == "refresh_plan"
    assert BusinessDocumentService._relation_action("cdr_drawing_snapshots", "frozen")["action"] == "preserve_fact_and_review"
    assert BusinessDocumentService._relation_action("source_item_refs", "active")["risk"] == "high"


def test_change_batch_summary_exposes_verification_history():
    version = SimpleNamespace(
        id=uuid4(),
        version_no=7,
        created_at=datetime(2026, 9, 2, 12, 0, 0),
        created_by=uuid4(),
        snapshot={
            "change_batch_id": "batch-1",
            "change_type": "order_item_update",
            "reason": "客户确认变更",
            "change_status": "PENDING_ADJUSTMENT",
            "status_history": ["PREVIEWED", "VERIFYING", "PENDING_ADJUSTMENT"],
            "verification_status": "PENDING_ADJUSTMENT",
            "before": {"total_amount": 100},
            "after": {"total_amount": 120},
            "refresh_result": {"counts": {"pending_review": 1}},
        },
    )

    result = BusinessDocumentService._change_batch_summary(version)

    assert result["change_batch_id"] == "batch-1"
    assert result["status_history"] == ["PREVIEWED", "VERIFYING", "PENDING_ADJUSTMENT"]
    assert result["counts"]["pending_review"] == 1


@pytest.mark.asyncio
async def test_change_batch_list_reports_total_beyond_page_limit():
    service = BusinessDocumentService(MagicMock(), doc_type="order")
    order = make_order()
    versions = [
        SimpleNamespace(
            id=uuid4(),
            version_no=index,
            created_at=datetime(2026, 9, 2, 12, index, 0),
            created_by=None,
            snapshot={
                "change_batch_id": f"batch-{index}",
                "change_status": "VERIFIED",
                "verification_status": "VERIFIED",
                "refresh_result": {"counts": {}},
            },
        )
        for index in (1, 2, 3)
    ]
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.db.execute = AsyncMock(
        return_value=FakeExecuteResult(scalar_rows=versions)
    )

    result = await service.list_order_item_change_batches(order.id, limit=1)

    assert result["total"] == 3
    assert len(result["batches"]) == 1


@pytest.mark.asyncio
async def test_pending_adjustment_submission_is_idempotent():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(item=item)
    service._get_locked_order = AsyncMock(return_value=order)
    service._find_applied_mutation = AsyncMock(return_value={
        "change_status": "PENDING_ADJUSTMENT",
        "refresh_result": {"counts": {"pending_review": 1}},
    })
    service.repo.get_by_id = AsyncMock(return_value=order)
    service._build_order_item_mutation_context = AsyncMock(
        side_effect=AssertionError("重复提交不应重新应用明细变更")
    )

    result = await service.mutate_order_item(
        order.id,
        "update",
        item_id=item.id,
        data={"quantity": 2},
        reason="重复提交测试",
        expected_updated_at="2026-09-02T10:00:00",
        preview_id="batch-1",
        plan_hash="not-needed-for-replay",
        preview_expires_at="2026-09-02T13:00:00",
    )

    assert result["change_batch"]["idempotent_replay"] is True
    assert result["change_batch"]["status"] == "PENDING_ADJUSTMENT"


class FakeExecuteResult:
    def __init__(self, *, scalar_value=None, scalar_rows=None, all_rows=None):
        self._scalar_value = scalar_value
        self._scalar_rows = scalar_rows or []
        self._all_rows = all_rows or []

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return self._scalar_rows if self._scalar_rows else self._all_rows


@pytest.mark.asyncio
async def test_order_reconciliation_checks_core_amounts_and_orphans():
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(item=item)
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    empty = FakeExecuteResult()
    db.execute = AsyncMock(side_effect=[
        FakeExecuteResult(all_rows=[(item.id, "active")]),
        FakeExecuteResult(scalar_value=Decimal("0")),
        FakeExecuteResult(scalar_value=0),
        FakeExecuteResult(scalar_value=Decimal("0")),
        FakeExecuteResult(scalar_value=0),
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        FakeExecuteResult(scalar_value=0),
        FakeExecuteResult(scalar_value=0),
        FakeExecuteResult(scalar_value=0),
        FakeExecuteResult(scalar_value=0),
        FakeExecuteResult(scalar_value=0),
        empty,
    ])

    result = await service.reconcile_order_item_change(order.id)

    assert result["status"] == "PASS"
    assert result["checks"]["order_total_equals_active_items"]["ok"] is True
    assert result["checks"]["no_orphan_item_references"]["ok"] is True


@pytest.mark.asyncio
async def test_stable_acceptance_and_outsource_links_refresh_only_planning_fields():
    db = MagicMock()
    db.flush = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    item_id = uuid4()
    acceptance_item = SimpleNamespace(
        id=uuid4(),
        document_item_id=item_id,
        item_status="pending",
        item_name="旧名称",
        material_process="旧工艺",
        specification="旧规格",
        quantity=Decimal("1"),
        unit="套",
        area=Decimal("1"),
        unit_price=Decimal("10"),
        subtotal=Decimal("10"),
        image_url=None,
        group_name=None,
    )
    form = SimpleNamespace(
        status="draft",
        acceptance_no="A-TEST-0001",
    )
    outsource = SimpleNamespace(
        id=uuid4(),
        order_item_id=item_id,
        status="pending",
        paid_amount=Decimal("0"),
        description="旧名称",
        task_no="OS-TEST-0001",
        quantity=1,
        unit_price=Decimal("10"),
        total_amount=Decimal("10"),
        unpaid_amount=Decimal("10"),
    )
    db.execute = AsyncMock(side_effect=[
        FakeExecuteResult(all_rows=[(acceptance_item, form)]),
        FakeExecuteResult(scalar_rows=[outsource]),
    ])

    result = await service._apply_order_item_refresh(
        make_order(status="in_production"),
        operation="update",
        item_id=item_id,
        projected_item={
            "item_name": "新名称",
            "material_process": "新工艺",
            "specification": "新规格",
            "quantity": Decimal("2"),
            "unit": "套",
            "area": Decimal("2"),
            "unit_price": Decimal("12"),
            "subtotal_amount": Decimal("24"),
            "image_url": "new.png",
            "group_name": "新分组",
        },
        relation_catalog=[
            {
                "module": "acceptance_items",
                "record_id": str(acceptance_item.id),
                "record_no": form.acceptance_no,
                "status": "pending",
                "action": "refresh_draft",
            },
            {
                "module": "outsource_tasks",
                "record_id": str(outsource.id),
                "record_no": outsource.task_no,
                "status": "pending",
                "action": "refresh_plan",
            },
        ],
        change_batch_id="batch-refresh",
    )

    assert result["status"] == "VERIFIED"
    assert result["counts"]["auto_refreshed"] == 2
    assert acceptance_item.item_name == "新名称"
    assert acceptance_item.subtotal == Decimal("24")
    assert outsource.quantity == 2
    # 订单明细单价是销售价，外协单价是供应商成本；刷新数量时沿用外协成本单价。
    assert outsource.total_amount == Decimal("20")


@pytest.mark.asyncio
async def test_order_item_recalculation_advances_parent_version():
    db = MagicMock()
    db.flush = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item(subtotal_amount=Decimal("100.00"))
    order = make_order(item=item)
    old_version = order.updated_at
    service.repo.get_items = AsyncMock(return_value=[item])
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))

    await service._recalculate_order_financials(order)

    assert order.updated_at != old_version
    db.flush.assert_awaited_once()


def test_order_item_request_requires_reason_and_version():
    with pytest.raises(Exception):
        OrderItemCreate(item_name="新增明细")

    request = OrderItemMutationPreview(
        operation="delete",
        item_id=str(uuid4()),
        reason="客户确认删除",
        expected_updated_at="2026-09-02T10:00:00",
    )
    assert request.operation == "delete"


@pytest.mark.asyncio
async def test_deleting_the_last_order_item_is_previewable_as_auto_recycle():
    """最后一条明细删除不是普通阻断，而是可确认的回收站动作。"""
    db = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    item = make_item()
    order = make_order(item=item)
    service.repo.get_by_id = AsyncMock(return_value=order)
    service.repo.get_items = AsyncMock(return_value=[item])
    service.repo.get_item = AsyncMock(return_value=item)
    service._collect_order_item_relations = AsyncMock(return_value=empty_relations())
    service._get_nonvoided_payment_total = AsyncMock(return_value=Decimal("0"))

    result = await service.preview_order_item_mutation(
        order.id,
        "delete",
        item_id=item.id,
        reason="客户确认删除最后一条明细",
        expected_updated_at="2026-09-02T10:00:00",
    )

    assert result["can_apply"] is True
    assert result["after"]["line_count"] == 0
    assert result["auto_recycle"] is True


@pytest.mark.asyncio
async def test_restore_auto_recycled_order_item_restores_task_link_and_scope():
    """Recycle-bin restore must undo the item/link/scope changes as one unit."""
    service = BusinessDocumentService(MagicMock(), doc_type="order")
    item_id = uuid4()
    task_id = uuid4()
    link_id = uuid4()
    item = SimpleNamespace(
        id=item_id,
        sort_order=0,
        lifecycle_status="voided",
        voided_at=datetime(2026, 9, 12, 10, 0, 0),
        void_reason="订单明细已删除，订单自动移入回收站",
        superseded_by_item_id=None,
    )
    task = SimpleNamespace(
        id=task_id,
        status="pending",
        progress_pct=0,
        completed_at=None,
        order_item_id=None,
        scope_status="empty_after_item_delete",
        scope_closed_at=datetime(2026, 9, 12, 10, 0, 0),
        scope_closed_reason="订单明细已删除",
    )
    link = SimpleNamespace(
        id=link_id,
        order_item_id=item_id,
        link_status="removed",
        removed_at=datetime(2026, 9, 12, 10, 0, 0),
        removed_by=uuid4(),
        removed_reason="订单明细已删除",
        position=9,
        assignee_user_id=None,
        item_status="pending",
        item_progress_pct=0,
        item_completed_at=None,
    )
    task_snapshot = {
        "task_type": "design",
        "task_id": str(task_id),
        "task_no": "D-TEST-0001",
        "link_id": str(link_id),
        "order_item_id": str(item_id),
        "task_order_item_id": str(item_id),
        "task_status": "designing",
        "task_progress_pct": 50,
        "task_completed_at": None,
        "task_scope_status": "active",
        "task_scope_closed_at": None,
        "task_scope_closed_reason": None,
        "position": 1,
        "assignee_user_id": None,
        "item_status": "designing",
        "item_progress_pct": 50,
        "item_completed_at": None,
    }
    version = SimpleNamespace(
        version_no=2,
        created_at=datetime(2026, 9, 12, 10, 0, 1),
        snapshot={
            "auto_recycled": True,
            "deleted_item_snapshots": [{"id": str(item_id)}],
            "task_link_snapshots": [task_snapshot],
        },
    )
    doc = SimpleNamespace(
        id=uuid4(),
        doc_type="order",
        versions=[version],
        items=[],
        design_tasks=[task],
        production_tasks=[],
        installation_tasks=[],
    )

    item_result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [item]),
    )
    service.db.execute = AsyncMock(return_value=item_result)
    service.db.get = AsyncMock(return_value=link)
    service.db.flush = AsyncMock()

    restored = await service._restore_order_item_delete_snapshot(doc)

    assert restored is True
    assert item.lifecycle_status == "active"
    assert item.voided_at is None
    assert item.void_reason is None
    assert doc.items == [item]
    assert link.link_status == "active"
    assert link.removed_at is None
    assert link.removed_by is None
    assert link.removed_reason is None
    assert link.position == 1
    assert link.item_status == "designing"
    assert link.item_progress_pct == 50
    assert task.order_item_id == item_id
    assert task.status == "designing"
    assert task.progress_pct == 50
    assert task.scope_status == "active"
    assert task.scope_closed_at is None
    assert task.scope_closed_reason is None


def test_order_item_task_scope_contract_has_removal_and_empty_scope_fields():
    from app.models.task import DesignTask, InstallationTask, ProductionTask

    link_columns = set(TaskOrderItemLink.__table__.columns.keys())
    assert {"link_status", "removed_at", "removed_by", "removed_reason"} <= link_columns
    for task_model in (DesignTask, ProductionTask, InstallationTask):
        assert {"scope_status", "scope_closed_at", "scope_closed_reason"} <= set(
            task_model.__table__.columns.keys()
        )


def test_order_to_quote_route_and_service_are_removed():
    import app.main as main

    assert not any("convert-to-quote" in path for path in main.app.openapi()["paths"])
    assert not hasattr(BusinessDocumentService, "convert_order_to_quote")


def test_order_item_change_batch_and_reconciliation_routes_are_registered():
    import app.main as main

    paths = main.app.openapi()["paths"]
    assert "/api/v1/orders/{order_id}/items/change-batches" in paths
    assert "/api/v1/orders/{order_id}/items/change-batches/{change_batch_id}" in paths
    assert "/api/v1/orders/{order_id}/items/reconciliation" in paths


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["completed", "cancelled"])
async def test_terminal_order_blocks_cost_and_contact_mutations(status):
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    service = BusinessDocumentService(db, doc_type="order")
    order = make_order(status=status)
    service.repo.get_by_id = AsyncMock(return_value=order)

    with pytest.raises(OrderDataMutationLocked, match="不允许修改成本"):
        await service.set_cost(order.id, 123)
    with pytest.raises(OrderDataMutationLocked, match="不允许修改联系人"):
        await service.update_order_contact(order.id, "新联系人", "13900000000")

    db.flush.assert_not_awaited()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_change_marks_linked_task_for_review_without_resetting_execution_state():
    db = MagicMock()
    db.flush = AsyncMock()
    task = SimpleNamespace(
        id=uuid4(),
        document_id=uuid4(),
        status="in_progress",
        progress_pct=60,
        assigned_to=uuid4(),
        scope_status="active",
        scope_closed_reason=None,
        production_no="P-REVIEW-0001",
    )
    db.execute = AsyncMock(return_value=FakeExecuteResult(scalar_rows=[task]))

    rows = await mark_tasks_for_order_review(
        db,
        task.document_id,
        order_item_id=uuid4(),
        changed_fields=["quantity", "width"],
        change_batch_id="batch-review-1",
        reason="客户确认调整数量",
        task_types={"production"},
    )

    assert len(rows) == 1
    assert rows[0]["action"] == "task_review_required"
    assert task_order_review_required(task) is True
    assert "数量" in task_order_review_reason(task)
    assert "宽度" in task_order_review_reason(task)
    assert "batch-review-1" in task_order_review_reason(task)
    assert task.status == "in_progress"
    assert task.progress_pct == 60
    assert task.assigned_to is not None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_completion_is_blocked_until_order_change_review_is_acknowledged():
    task = SimpleNamespace(
        status="in_progress",
        scope_status="active",
        scope_closed_reason=f"{TASK_ORDER_REVIEW_PREFIX}批次 batch-review-2，需复核：数量",
    )

    with pytest.raises(ValueError, match="订单变更待复核"):
        await _apply_task_item_status_change(
            MagicMock(),
            "production",
            task,
            "completed",
            [str(uuid4())],
        )
