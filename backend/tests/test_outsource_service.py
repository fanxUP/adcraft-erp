"""Tests for OutsourceService: vendor/task/payment CRUD."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.outsource import OutsourcePaymentCreate, OutsourceTaskCreate
from app.services.outsource_service import OutsourceService
from tests.conftest import (
    SAMPLE_USER_ID,
    SAMPLE_ORDER_ID,
    SAMPLE_TASK_ID,
    make_mock_design_task,
)


SAMPLE_ORDER_ITEM_ID = UUID("55555555-5555-5555-5555-555555555555")


def make_mock_vendor(**kwargs):
    v = MagicMock()
    v.id = kwargs.get("id", SAMPLE_USER_ID)
    v.vendor_no = kwargs.get("vendor_no", "V20260629-0001")
    v.name = kwargs.get("name", "测试外协商")
    v.contact_person = kwargs.get("contact_person", "王经理")
    v.phone = kwargs.get("phone", "13900139000")
    v.address = kwargs.get("address", "深圳市宝安区")
    v.service_type = kwargs.get("service_type", "加工")
    v.coop_rating = kwargs.get("coop_rating", "A")
    v.remark = kwargs.get("remark")
    v.is_active = kwargs.get("is_active", True)
    v.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return v


def make_mock_outsource_task(**kwargs):
    t = MagicMock()
    t.id = kwargs.get("id", SAMPLE_ORDER_ID)
    t.task_no = kwargs.get("task_no", "OT20260629-0001")
    t.vendor_id = kwargs.get("vendor_id", SAMPLE_USER_ID)
    t.order_id = kwargs.get("order_id", SAMPLE_ORDER_ID)
    t.related_doc_id = kwargs.get("related_doc_id", SAMPLE_ORDER_ID)
    t.related_doc_type = kwargs.get("related_doc_type", "order")
    t.order_item_id = kwargs.get("order_item_id")
    t.order_item = kwargs.get("order_item")
    t.task_type = kwargs.get("task_type", "laser_cutting")
    t.description = kwargs.get("description", "激光切割")
    t.quantity = kwargs.get("quantity", 10.0)
    t.unit_price = kwargs.get("unit_price", 50.0)
    t.total_amount = kwargs.get("total_amount", 500.0)
    t.paid_amount = kwargs.get("paid_amount", 0.0)
    t.unpaid_amount = kwargs.get("unpaid_amount", float(t.total_amount) - float(t.paid_amount))
    t.status = kwargs.get("status", "pending")
    t.expected_at = kwargs.get("expected_at")
    t.completed_at = kwargs.get("completed_at")
    t.remark = kwargs.get("remark")
    t.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    t.deleted_at = kwargs.get("deleted_at")
    t.source_task_type = kwargs.get("source_task_type")
    t.source_task_id = kwargs.get("source_task_id")
    return t


def make_mock_outsource_payment(**kwargs):
    p = MagicMock()
    p.id = kwargs.get("id", SAMPLE_USER_ID)
    p.payment_no = kwargs.get("payment_no", "OP20260629-0001")
    p.vendor_id = kwargs.get("vendor_id", SAMPLE_USER_ID)
    p.task_id = kwargs.get("task_id", SAMPLE_ORDER_ID)
    p.amount = kwargs.get("amount", 500.0)
    p.payment_method = kwargs.get("payment_method", "bank_transfer")
    p.paid_at = kwargs.get("paid_at", datetime.now(timezone.utc))
    p.remark = kwargs.get("remark")
    p.created_by = kwargs.get("created_by", SAMPLE_USER_ID)
    p.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return p


@pytest.fixture
def mock_repos():
    vendor_repo = MagicMock()
    vendor_repo.get_by_id = AsyncMock()
    vendor_repo.list_vendors = AsyncMock(return_value=([], 0))
    vendor_repo.create = AsyncMock()
    vendor_repo.update = AsyncMock()
    vendor_repo.soft_delete = AsyncMock()

    async def vendor_update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj
    vendor_repo.update.side_effect = vendor_update_side_effect

    task_repo = MagicMock()
    task_repo.get_by_id = AsyncMock()
    task_repo.list_tasks = AsyncMock(return_value=([], 0))
    task_repo.list_task_groups = AsyncMock(return_value=([], 0))
    task_repo.list_task_group_tasks = AsyncMock(return_value=([], 0))
    task_repo.create = AsyncMock()
    task_repo.get_deleted_by_id = AsyncMock()
    task_repo.restore = AsyncMock()
    task_repo.soft_delete = AsyncMock()

    async def task_update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj
    task_repo.update.side_effect = task_update_side_effect

    payment_repo = MagicMock()
    payment_repo.list_payments = AsyncMock(return_value=([], 0))
    payment_repo.create = AsyncMock()
    payment_repo.payment_totals = AsyncMock(return_value=(0, 0.0))
    payment_repo.delete_by_task = AsyncMock()

    return vendor_repo, task_repo, payment_repo


@pytest.fixture
def service(mock_repos):
    vendor_repo, task_repo, payment_repo = mock_repos
    with patch("app.services.outsource_service.OutsourceVendorRepository") as MockVendorRepo, \
         patch("app.services.outsource_service.OutsourceTaskRepository") as MockTaskRepo, \
         patch("app.services.outsource_service.OutsourcePaymentRepository") as MockPaymentRepo:
        MockVendorRepo.return_value = vendor_repo
        MockTaskRepo.return_value = task_repo
        MockPaymentRepo.return_value = payment_repo
        db = AsyncMock()
        # Mock _vendor_name lookup
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "测试外协商"
        db.execute = AsyncMock(return_value=name_result)

        svc = OutsourceService(db)
        svc.vendor_repo = vendor_repo
        svc.task_repo = task_repo
        svc.payment_repo = payment_repo
        yield svc, vendor_repo, task_repo, payment_repo


# ════════════════════════════════════════════════
# Vendor Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_vendors_empty(service):
    svc, vr, _, _ = service
    vr.list_vendors.return_value = ([], 0)
    items, total = await svc.list_vendors(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_vendor_found(service):
    svc, vr, _, _ = service
    v = make_mock_vendor()
    vr.get_by_id.return_value = v
    result = await svc.get_vendor(SAMPLE_USER_ID)
    assert result is not None
    assert result["name"] == "测试外协商"
    assert result["vendor_no"] == "V20260629-0001"


@pytest.mark.asyncio
async def test_get_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    result = await svc.get_vendor(SAMPLE_USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_vendor(service):
    svc, vr, _, _ = service
    vr.create.return_value = make_mock_vendor(name="新外协商")
    with patch("app.services.outsource_service.generate_vendor_no", AsyncMock(return_value="V20260629-0002")):
        result = await svc.create_vendor({"name": "新外协商"})
    assert result["name"] == "新外协商"


@pytest.mark.asyncio
async def test_update_vendor(service):
    svc, vr, _, _ = service
    v = make_mock_vendor(name="旧名称")
    vr.get_by_id.return_value = v
    result = await svc.update_vendor(SAMPLE_USER_ID, {"name": "新名称"})
    assert result["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    with pytest.raises(ValueError, match="外协商不存在"):
        await svc.update_vendor(SAMPLE_USER_ID, {"name": "新名称"})


@pytest.mark.asyncio
async def test_delete_vendor_success(service):
    svc, vr, _, _ = service
    v = make_mock_vendor()
    vr.get_by_id.return_value = v
    result = await svc.delete_vendor(SAMPLE_USER_ID)
    assert result is True
    vr.soft_delete.assert_awaited_once_with(v)


@pytest.mark.asyncio
async def test_delete_vendor_not_found(service):
    svc, vr, _, _ = service
    vr.get_by_id.return_value = None
    result = await svc.delete_vendor(SAMPLE_USER_ID)
    assert result is False


# ════════════════════════════════════════════════
# Task Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_tasks_empty(service):
    svc, _, tr, _ = service
    tr.list_tasks.return_value = ([], 0)
    items, total = await svc.list_tasks(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_task_groups_resolves_source_business_number_and_summaries(service):
    """同一内部任务下的外协记录应显示来源业务编号并汇总可核对金额。"""
    svc, _, tr, _ = service
    tr.list_task_groups = AsyncMock(
        return_value=(
            [
                SimpleNamespace(
                    group_key=f"source:design:{SAMPLE_TASK_ID}",
                    group_kind="source_task",
                    task_count=2,
                    active_task_count=2,
                    status_pending_count=1,
                    status_in_progress_count=0,
                    status_completed_count=1,
                    status_settled_count=0,
                    status_cancelled_count=0,
                    status_other_count=0,
                    planned_amount=Decimal("120"),
                    recognized_cost=Decimal("80"),
                    paid_amount=Decimal("20"),
                    unpaid_amount=Decimal("100"),
                    related_doc_ids=[SAMPLE_ORDER_ID],
                    latest_created_at=datetime.now(timezone.utc),
                ),
            ],
            1,
        )
    )
    source_task = make_mock_design_task(
        task_id=SAMPLE_TASK_ID,
        design_no="D20260903-0001",
        order_id=SAMPLE_ORDER_ID,
        project_name="测试设计项目",
        status="in_progress",
    )
    source_result = MagicMock()
    source_result.scalars.return_value.all.return_value = [source_task]
    document = MagicMock(
        id=SAMPLE_ORDER_ID,
        doc_no="O20260903-0001",
        doc_type="order",
        project_name="测试设计项目",
    )
    document_result = MagicMock()
    document_result.scalars.return_value.all.return_value = [document]
    svc.db.execute = AsyncMock(side_effect=[source_result, document_result])

    groups, total = await svc.list_task_groups(page=1, page_size=20)

    assert total == 1
    assert groups[0]["group_key"] == f"source:design:{SAMPLE_TASK_ID}"
    assert groups[0]["source_task_no"] == "D20260903-0001"
    assert groups[0]["source_task_status"] == "in_progress"
    assert groups[0]["related_doc_no"] == "O20260903-0001"
    assert groups[0]["planned_amount"] == 120.0
    assert groups[0]["recognized_cost"] == 80.0
    assert groups[0]["paid_amount"] == 20.0
    assert groups[0]["unpaid_amount"] == 100.0
    assert groups[0]["status_counts"] == {
        "pending": 1,
        "in_progress": 0,
        "completed": 1,
        "settled": 0,
        "cancelled": 0,
        "other": 0,
    }


@pytest.mark.asyncio
async def test_list_task_group_tasks_rejects_untrusted_group_key(service):
    """分组明细接口不能接受未经严格校验的键，避免越权/模糊匹配。"""
    svc, _, tr, _ = service
    tr.list_task_group_tasks = AsyncMock()

    with pytest.raises(ValueError, match="无效的外协任务分组"):
        await svc.list_task_group_tasks("source:design:not-a-uuid", page=1, page_size=20)

    with pytest.raises(ValueError, match="分组与来源任务类型筛选不一致"):
        await svc.list_task_group_tasks(
            f"source:design:{SAMPLE_TASK_ID}",
            page=1,
            page_size=20,
            source_task_type="production",
        )

    tr.list_task_group_tasks.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_task_groups_keeps_legacy_document_fallback_visible(service):
    """历史无来源任务记录按单据兜底，并明确标记单据缺失风险。"""
    svc, _, tr, _ = service
    legacy_doc_id = UUID("66666666-6666-6666-6666-666666666666")
    tr.list_task_groups.return_value = (
        [
            SimpleNamespace(
                group_key=f"document:order:{legacy_doc_id}",
                group_kind="related_document",
                task_count=1,
                active_task_count=1,
                planned_amount=Decimal("50"),
                recognized_cost=Decimal("0"),
                paid_amount=Decimal("0"),
                unpaid_amount=Decimal("50"),
                related_doc_ids=[legacy_doc_id],
            ),
        ],
        1,
    )
    missing_document_result = MagicMock()
    missing_document_result.scalars.return_value.all.return_value = []
    svc.db.execute = AsyncMock(return_value=missing_document_result)

    groups, total = await svc.list_task_groups(page=1, page_size=20)

    assert total == 1
    assert groups[0]["group_kind"] == "related_document"
    assert groups[0]["group_label"] == f"订单 {legacy_doc_id} · 未关联来源任务"
    assert groups[0]["related_doc_type"] == "order"
    assert groups[0]["related_doc_id"] == str(legacy_doc_id)
    assert groups[0]["consistency_warning"] == "关联单据已不存在"


@pytest.mark.asyncio
async def test_list_task_group_tasks_passes_group_and_filters(service):
    """组内明细查询继续透传现有筛选条件，并返回现有明细格式。"""
    svc, _, tr, _ = service
    task = make_mock_outsource_task(source_task_type="design", source_task_id=SAMPLE_TASK_ID)
    tr.list_task_group_tasks.return_value = ([task], 1)

    items, total = await svc.list_task_group_tasks(
        f"source:design:{SAMPLE_TASK_ID}",
        page=2,
        page_size=10,
        status="pending",
        source_task_type="design",
        source_task_id=SAMPLE_TASK_ID,
        task_type="design",
    )

    assert total == 1
    assert items[0]["task_no"] == task.task_no
    args = tr.list_task_group_tasks.call_args.args
    assert args[:3] == (f"source:design:{SAMPLE_TASK_ID}", 10, 10)
    assert args[3] == "pending"
    assert args[6] == "design"
    assert args[7] == SAMPLE_TASK_ID


@pytest.mark.asyncio
async def test_get_task_found(service):
    svc, _, tr, _ = service
    t = make_mock_outsource_task()
    tr.get_by_id.return_value = t
    result = await svc.get_task(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["task_no"] == "OT20260629-0001"


@pytest.mark.asyncio
async def test_get_task_not_found(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = None
    result = await svc.get_task(SAMPLE_ORDER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_task(service):
    svc, _, tr, _ = service
    tr.create.return_value = make_mock_outsource_task(
        task_no="OT20260629-0002", quantity=5, unit_price=100.0, total_amount=500.0
    )
    with patch("app.services.outsource_service.generate_outsource_task_no", AsyncMock(return_value="OT20260629-0002")):
        result = await svc.create_task({
            "vendor_id": SAMPLE_USER_ID,
            "order_id": SAMPLE_ORDER_ID,
            "task_type": "laser_cutting",
            "quantity": 5,
            "unit_price": 100.0,
        })
    assert result["task_no"] == "OT20260629-0002"


@pytest.mark.asyncio
async def test_create_task_accepts_item_owned_by_selected_order(service):
    svc, _, task_repo, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=SAMPLE_ORDER_ID,
        item_name="户外写真",
        lifecycle_status="active",
    )
    svc.db.get = AsyncMock(side_effect=[order, item])
    task_repo.create.return_value = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        order_item=item,
    )

    with patch(
        "app.services.outsource_service.generate_outsource_task_no",
        AsyncMock(return_value="OT20260902-0001"),
    ):
        result = await svc.create_task(
            {
                "vendor_id": SAMPLE_USER_ID,
                "related_doc_id": SAMPLE_ORDER_ID,
                "related_doc_type": "order",
                "order_item_id": SAMPLE_ORDER_ITEM_ID,
                "task_type": "production",
                "quantity": Decimal("1.25"),
                "unit_price": 100,
            }
        )

    assert result["order_item_id"] == str(SAMPLE_ORDER_ITEM_ID)
    assert result["order_item_name"] == "户外写真"
    assert task_repo.create.await_args.args[0]["order_item_id"] == SAMPLE_ORDER_ITEM_ID


@pytest.mark.asyncio
async def test_create_task_rejects_item_from_another_order(service):
    svc, _, task_repo, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    foreign_item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=UUID("66666666-6666-6666-6666-666666666666"),
        item_name="其他订单明细",
        lifecycle_status="active",
    )
    svc.db.get = AsyncMock(side_effect=[order, foreign_item])

    with patch(
        "app.services.outsource_service.generate_outsource_task_no",
        AsyncMock(return_value="OT20260902-0002"),
    ):
        with pytest.raises(ValueError, match="不属于所选订单"):
            await svc.create_task(
                {
                    "vendor_id": SAMPLE_USER_ID,
                    "related_doc_id": SAMPLE_ORDER_ID,
                    "related_doc_type": "order",
                    "order_item_id": SAMPLE_ORDER_ITEM_ID,
                    "task_type": "production",
                    "quantity": 1,
                    "unit_price": 100,
                }
            )

    task_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_task_can_explicitly_clear_unpaid_item_link(service):
    svc, _, task_repo, _ = service
    task = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        paid_amount=0,
        unpaid_amount=100,
    )
    task_repo.get_by_id.return_value = task

    result = await svc.update_task(SAMPLE_ORDER_ID, {"order_item_id": None})

    assert result["order_item_id"] is None
    task_repo.update.assert_called_once()
    assert task_repo.update.call_args.args[1]["order_item_id"] is None


@pytest.mark.asyncio
async def test_update_task_rejects_paid_item_reassignment(service):
    svc, _, task_repo, _ = service
    task_repo.get_by_id.return_value = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        paid_amount=10,
    )

    with pytest.raises(ValueError, match="已有付款的外协任务不能更换订单明细"):
        await svc.update_task(
            SAMPLE_ORDER_ID,
            {"order_item_id": UUID("77777777-7777-7777-7777-777777777777")},
        )


@pytest.mark.asyncio
async def test_order_item_summary_reports_partial_allocation_and_costs(service):
    svc, _, _, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    first_item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=SAMPLE_ORDER_ID,
        item_name="户外写真",
        quantity=Decimal("3"),
        unit="套",
        group_name="制作",
        sort_order=0,
        lifecycle_status="active",
    )
    second_item_id = UUID("88888888-8888-8888-8888-888888888888")
    second_item = MagicMock(
        id=second_item_id,
        document_id=SAMPLE_ORDER_ID,
        item_name="安装服务",
        quantity=Decimal("1"),
        unit="项",
        group_name="安装",
        sort_order=1,
        lifecycle_status="active",
    )
    pending = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        quantity=Decimal("1.25"),
        unit_price=Decimal("100"),
        total_amount=Decimal("125"),
        status="pending",
    )
    completed = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        total_amount=Decimal("100"),
        status="completed",
    )
    finished = make_mock_outsource_task(
        order_item_id=second_item_id,
        quantity=Decimal("1"),
        unit_price=Decimal("20"),
        total_amount=Decimal("20"),
        status="settled",
    )
    item_result = MagicMock()
    item_result.scalars.return_value.all.return_value = [first_item, second_item]
    task_result = MagicMock()
    task_result.scalars.return_value.all.return_value = [pending, completed, finished]
    svc.db.get = AsyncMock(return_value=order)
    order_level_result = MagicMock()
    order_level_result.scalars.return_value.all.return_value = []
    svc.db.execute = AsyncMock(side_effect=[item_result, task_result, order_level_result])

    result = await svc.get_order_item_summary(
        SAMPLE_ORDER_ID,
        task_type="production",
        source_task_type="production",
        source_task_id=SAMPLE_TASK_ID,
    )

    assert result["task_type"] == "production"
    assert result["items"][0]["allocated_quantity"] == 2.25
    assert result["items"][0]["remaining_quantity"] == 0.75
    assert result["items"][0]["planned_amount"] == 225.0
    assert result["items"][0]["recognized_cost"] == 100.0
    assert result["items"][0]["status"] == "部分外协"
    assert result["items"][0]["requires_reason"] is False
    assert result["items"][1]["status"] == "已完成"
    assert result["items"][1]["requires_reason"] is True


@pytest.mark.asyncio
async def test_send_order_item_defaults_to_remaining_quantity(service):
    svc, _, task_repo, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=SAMPLE_ORDER_ID,
        item_name="户外写真",
        quantity=Decimal("3"),
        lifecycle_status="active",
    )
    source_task = MagicMock(document_id=SAMPLE_ORDER_ID)
    existing = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        quantity=Decimal("1.25"),
        total_amount=Decimal("125"),
    )
    existing_result = MagicMock()
    existing_result.scalars.return_value.all.return_value = [existing]
    vendor_result = MagicMock()
    vendor_result.scalar_one_or_none.return_value = "测试外协商"
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = "测试订单"
    task_repo.create.return_value = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        order_item=item,
        quantity=Decimal("1.75"),
    )
    item_lock_result = MagicMock()
    item_lock_result.scalar_one_or_none.return_value = item
    svc.db.get = AsyncMock(side_effect=[order, source_task])
    svc.db.execute = AsyncMock(side_effect=[item_lock_result, existing_result, vendor_result, project_result])

    with patch(
        "app.services.outsource_service.generate_outsource_task_no",
        AsyncMock(return_value="OT20260902-0003"),
    ):
        await svc.send_order_item(
            SAMPLE_ORDER_ID,
            SAMPLE_ORDER_ITEM_ID,
            {
                "vendor_id": SAMPLE_USER_ID,
                "task_type": "production",
                "source_task_type": "production",
                "source_task_id": SAMPLE_TASK_ID,
                "unit_price": Decimal("80"),
            },
        )

    create_data = task_repo.create.await_args.args[0]
    assert create_data["quantity"] == Decimal("1.75")
    assert create_data["order_item_id"] == SAMPLE_ORDER_ITEM_ID
    assert create_data["related_doc_id"] == SAMPLE_ORDER_ID
    assert create_data["source_task_id"] == SAMPLE_TASK_ID


@pytest.mark.asyncio
async def test_update_task_with_unit_price_change(service):
    svc, _, tr, _ = service
    t = make_mock_outsource_task(quantity=10, unit_price=50.0, total_amount=500.0)
    tr.get_by_id.return_value = t

    result = await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 60.0})
    # total_amount should be recalculated: 10 * 60 = 600
    assert result["total_amount"] == 600.0


@pytest.mark.asyncio
async def test_update_task_recalculates_unpaid_amount(service):
    svc, _, tr, _ = service
    task = make_mock_outsource_task(
        quantity=10,
        unit_price=50.0,
        total_amount=500.0,
        paid_amount=200.0,
        unpaid_amount=300.0,
    )
    tr.get_by_id.return_value = task

    result = await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 60.0})

    assert result["total_amount"] == 600.0
    assert result["paid_amount"] == 200.0
    assert result["unpaid_amount"] == 400.0


@pytest.mark.asyncio
async def test_update_task_rejects_total_below_paid_amount(service):
    svc, _, tr, _ = service
    task = make_mock_outsource_task(
        quantity=10,
        unit_price=50.0,
        total_amount=500.0,
        paid_amount=400.0,
        unpaid_amount=100.0,
    )
    tr.get_by_id.return_value = task

    with pytest.raises(ValueError, match="不能低于已付金额"):
        await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 30.0})


@pytest.mark.asyncio
async def test_update_task_rejects_status_jump(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = make_mock_outsource_task(status="pending")

    with pytest.raises(ValueError, match="不允许从 pending 流转到 completed"):
        await svc.update_task(SAMPLE_ORDER_ID, {"status": "completed"})


@pytest.mark.asyncio
async def test_update_task_cannot_reactivate_cancelled_task(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = make_mock_outsource_task(status="cancelled")

    with pytest.raises(ValueError, match="已取消的外协任务不能编辑"):
        await svc.update_task(SAMPLE_ORDER_ID, {"remark": "绕过恢复"})


@pytest.mark.asyncio
async def test_completing_fully_paid_task_marks_it_settled(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = make_mock_outsource_task(
        status="in_progress",
        paid_amount=500.0,
        unpaid_amount=0.0,
    )

    result = await svc.update_task(SAMPLE_ORDER_ID, {"status": "completed"})

    assert result["status"] == "settled"
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_task_not_found(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = None
    with pytest.raises(ValueError, match="外协任务不存在"):
        await svc.update_task(SAMPLE_ORDER_ID, {"unit_price": 60.0})


# ════════════════════════════════════════════════
# Payment Tests
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_payments_empty(service):
    svc, _, _, pr = service
    pr.list_payments.return_value = ([], 0)
    items, total = await svc.list_payments(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_payment(service):
    svc, _, _, pr = service
    pr.create.return_value = make_mock_outsource_payment(payment_no="OP20260629-0002")
    with patch("app.services.outsource_service.generate_outsource_payment_no", AsyncMock(return_value="OP20260629-0002")):
        result = await svc.create_payment({
            "vendor_id": SAMPLE_USER_ID,
            "amount": 500.0,
        })
    assert result["payment_no"] == "OP20260629-0002"


@pytest.mark.asyncio
async def test_create_payment_rejects_vendor_mismatch(service):
    svc, _, tr, _ = service
    task = make_mock_outsource_task(vendor_id=SAMPLE_USER_ID)
    tr.get_by_id.return_value = task

    with pytest.raises(ValueError, match="付款供应商与外协任务不一致"):
        await svc.create_payment({
            "vendor_id": "99999999-9999-9999-9999-999999999999",
            "task_id": SAMPLE_ORDER_ID,
            "amount": 100,
        })


@pytest.mark.asyncio
async def test_create_payment_rejects_amount_above_task_balance(service):
    svc, _, tr, _ = service
    task = make_mock_outsource_task(
        total_amount=500.0,
        paid_amount=400.0,
        unpaid_amount=100.0,
    )
    tr.get_by_id.return_value = task

    with pytest.raises(ValueError, match="超过任务未付金额"):
        await svc.create_payment({
            "vendor_id": SAMPLE_USER_ID,
            "task_id": SAMPLE_ORDER_ID,
            "amount": 101,
        })


@pytest.mark.asyncio
async def test_create_payment_updates_balance_and_creator(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(
        total_amount=500.0,
        paid_amount=100.0,
        unpaid_amount=400.0,
    )
    tr.get_by_id.return_value = task
    pr.create.return_value = make_mock_outsource_payment(amount=150.0)

    with patch(
        "app.services.outsource_service.generate_outsource_payment_no",
        AsyncMock(return_value="OP20260629-0002"),
    ):
        await svc.create_payment(
            {
                "vendor_id": SAMPLE_USER_ID,
                "task_id": SAMPLE_ORDER_ID,
                "amount": 150,
            },
            created_by=SAMPLE_USER_ID,
        )

    create_data = pr.create.await_args.args[0]
    assert create_data["created_by"] == SAMPLE_USER_ID
    assert task.paid_amount == 250.0
    assert task.unpaid_amount == 250.0


@pytest.mark.asyncio
async def test_full_payment_settles_completed_task(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(
        status="completed",
        total_amount=500.0,
        paid_amount=400.0,
        unpaid_amount=100.0,
    )
    tr.get_by_id.return_value = task
    pr.create.return_value = make_mock_outsource_payment(amount=100.0)

    with patch(
        "app.services.outsource_service.generate_outsource_payment_no",
        AsyncMock(return_value="OP20260629-0002"),
    ):
        await svc.create_payment({
            "vendor_id": SAMPLE_USER_ID,
            "task_id": SAMPLE_ORDER_ID,
            "amount": 100,
        })

    assert task.status == "settled"


@pytest.mark.asyncio
async def test_cancel_task_rejects_task_with_payment(service):
    svc, _, tr, _ = service
    tr.get_by_id.return_value = make_mock_outsource_task(paid_amount=100.0)

    with pytest.raises(ValueError, match="已有付款"):
        await svc.cancel_task(SAMPLE_ORDER_ID)


@pytest.mark.asyncio
async def test_delete_task_any_status_cascades_payments(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(status="settled")
    tr.get_by_id.return_value = task
    pr.payment_totals = AsyncMock(return_value=(2, 500.0))
    pr.delete_by_task = AsyncMock()

    result = await svc.delete_task(SAMPLE_ORDER_ID)

    pr.delete_by_task.assert_awaited_once_with(SAMPLE_ORDER_ID)
    tr.soft_delete.assert_awaited_once_with(task)
    assert result["deleted_payment_count"] == 2
    assert result["deleted_payment_total"] == 500.0


@pytest.mark.asyncio
async def test_delete_task_without_payments(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(status="settled")
    tr.get_by_id.return_value = task
    pr.payment_totals = AsyncMock(return_value=(0, 0.0))
    pr.delete_by_task = AsyncMock()

    result = await svc.delete_task(SAMPLE_ORDER_ID)

    pr.delete_by_task.assert_not_awaited()
    tr.soft_delete.assert_awaited_once_with(task)
    assert result["deleted_payment_count"] == 0
    assert result["deleted_payment_total"] == 0.0


@pytest.mark.asyncio
async def test_restore_task_keeps_cancelled_status(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(status="cancelled", deleted_at=datetime.now(timezone.utc))
    tr.get_deleted_by_id.return_value = task
    pr.payment_totals = AsyncMock(return_value=(0, 0.0))

    result = await svc.restore_task(SAMPLE_ORDER_ID)

    assert result["status"] == "cancelled"
    tr.restore.assert_awaited_once_with(task)


@pytest.mark.asyncio
async def test_restore_task_recomputes_amounts_from_remaining_payments(service):
    svc, _, tr, pr = service
    task = make_mock_outsource_task(
        status="cancelled",
        total_amount=500.0,
        paid_amount=500.0,
        unpaid_amount=0.0,
        deleted_at=datetime.now(timezone.utc),
    )
    tr.get_deleted_by_id.return_value = task
    # 付款已随删除清除，恢复后已付/未付按现存付款重算为 0
    pr.payment_totals = AsyncMock(return_value=(0, 0.0))

    result = await svc.restore_task(SAMPLE_ORDER_ID)

    assert result["paid_amount"] == 0.0
    assert result["unpaid_amount"] == 500.0
    tr.restore.assert_awaited_once_with(task)


def test_outsource_amounts_and_quantity_must_be_valid():
    with pytest.raises(ValidationError):
        OutsourcePaymentCreate(vendor_id=str(SAMPLE_USER_ID), amount=0)
    with pytest.raises(ValidationError):
        OutsourceTaskCreate(
            vendor_id=str(SAMPLE_USER_ID),
            task_type="production",
            quantity=0,
            unit_price=1,
        )
    with pytest.raises(ValidationError):
        OutsourceTaskCreate(
            vendor_id=str(SAMPLE_USER_ID),
            task_type="production",
            quantity=1,
            unit_price=-1,
        )


@pytest.mark.asyncio
async def test_create_task_passes_source_task_fields(service):
    """create_task 透传 source_task_type/source_task_id 并回显到响应。"""
    svc, _, tr, _ = service
    svc.db.get = AsyncMock(return_value=MagicMock(document_id=SAMPLE_ORDER_ID))
    tr.create.return_value = make_mock_outsource_task(
        task_no="OT20260629-0003",
        source_task_type="design",
        source_task_id=SAMPLE_TASK_ID,
    )
    with patch("app.services.outsource_service.generate_outsource_task_no", AsyncMock(return_value="OT20260629-0003")):
        result = await svc.create_task({
            "vendor_id": SAMPLE_USER_ID,
            "order_id": SAMPLE_ORDER_ID,
            "task_type": "design",
            "quantity": 1,
            "unit_price": 0,
            "source_task_type": "design",
            "source_task_id": SAMPLE_TASK_ID,
        })
    assert result["source_task_type"] == "design"
    assert result["source_task_id"] == str(SAMPLE_TASK_ID)
    data = tr.create.call_args.args[0]
    assert data["source_task_type"] == "design"
    assert data["source_task_id"] == SAMPLE_TASK_ID


@pytest.mark.asyncio
async def test_list_tasks_passes_source_filter(service):
    """list_tasks 把 source_task_type/source_task_id 过滤透传给 repo。"""
    svc, _, tr, _ = service
    tr.list_tasks.return_value = ([make_mock_outsource_task()], 1)
    items, total = await svc.list_tasks(
        page=1, page_size=20,
        source_task_type="design",
        source_task_id=SAMPLE_TASK_ID,
    )
    assert total == 1
    assert len(items) == 1
    args = tr.list_tasks.call_args.args
    # (skip, limit, status, vendor_id, related_doc_id, source_task_type, source_task_id)
    assert args[5] == "design"
    assert args[6] == SAMPLE_TASK_ID


@pytest.mark.asyncio
async def test_list_tasks_passes_task_type_filter(service):
    """list_tasks 把外协任务类型筛选透传给 repo。"""
    svc, _, tr, _ = service
    tr.list_tasks.return_value = ([], 0)

    items, total = await svc.list_tasks(page=1, page_size=20, task_type="design")

    assert items == []
    assert total == 0
    args = tr.list_tasks.call_args.args
    assert args[7] == "design"
