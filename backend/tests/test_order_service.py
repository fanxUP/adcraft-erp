"""统一业务单据服务的订单路径回归测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.business_document_service import BusinessDocumentService, ORDER_TRANSITIONS
from app.models.task import ProductionTask
from app.models.acceptance import AcceptanceForm
from app.models.user import User
from app.services.task_service import DesignTaskService
from tests.conftest import SAMPLE_CUSTOMER_ID, SAMPLE_ORDER_ID


def make_order(**overrides):
    order = MagicMock()
    defaults = {
        "id": SAMPLE_ORDER_ID,
        "doc_type": "order",
        "doc_no": "O20260629-0001",
        "customer_id": SAMPLE_CUSTOMER_ID,
        "customer_name": None,
        "project_name": "测试订单",
        "department": None,
        "contact_person": None,
        "contact_phone": None,
        "status": "pending_confirm",
        "total_amount": Decimal("1000"),
        "paid_amount": Decimal("0"),
        "unpaid_amount": Decimal("1000"),
        "cost_amount": Decimal("0"),
        "gross_profit": Decimal("1000"),
        "sales_user_id": None,
        "delivery_deadline": None,
        "installation_address": None,
        "remark": None,
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
        "customer": None,
        "items": [],
        "status_logs": [],
        "design_tasks": [],
        "production_tasks": [],
        "installation_tasks": [],
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(order, key, value)
    return order


def test_order_completes_directly_after_installation():
    assert "completed" in ORDER_TRANSITIONS["in_installation"]
    assert "pending_acceptance" not in ORDER_TRANSITIONS


@pytest.fixture
def service():
    db = MagicMock()
    db.execute = AsyncMock()
    db.refresh = AsyncMock()
    with patch(
        "app.services.business_document_service.BusinessDocumentRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.get_by_id = AsyncMock()
        repository.list_all = AsyncMock(return_value=([], 0))
        repository.create_status_log = AsyncMock()

        async def update(document, data):
            for key, value in data.items():
                setattr(document, key, value)
            return document

        repository.update = AsyncMock(side_effect=update)
        yield BusinessDocumentService(db, doc_type="order"), repository, db



@pytest.mark.asyncio
async def test_confirmed_design_task_unlocks_order_production(service):
    """DesignTaskService auto-creates production task & advances order on confirmation."""
    # Patch ProductionTask.__init__ to avoid SQLAlchemy mapper resolution chain
    with patch.object(ProductionTask, "__init__", return_value=None):
        order_service, repository, db = service
        db.flush = AsyncMock()
        db.add = MagicMock()
        order = make_order(status="designing")
        repository.get_by_id.return_value = order

        design_task = MagicMock()
        design_task.id = uuid4()
        design_task.document_id = order.id
        design_task.design_no = "D20260729-0001"
        design_task.status = "pending"
        design_task.completed_at = None

        call_count = [0]
        def mock_execute(*a, **kw):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                r.scalar.return_value = 0
            else:
                r.scalar_one_or_none.return_value = None
            return r

        db.execute = AsyncMock(side_effect=mock_execute)

        async def mock_db_get(model, doc_id, **kw):
            return order
        db.get = AsyncMock(side_effect=mock_db_get)

        design_service = DesignTaskService(db)
        design_service.repo = MagicMock()
        design_service.repo.get_by_id = AsyncMock(return_value=design_task)
        design_service._to_dict = AsyncMock(
            side_effect=lambda task: {"status": task.status}
        )

        await design_service.change_status(design_task.id, "designing")
        await design_service.change_status(design_task.id, "pending_review")
        await design_service.change_status(design_task.id, "confirmed")

        assert order.status == "in_production", f"Expected in_production, got {order.status}"
        db.add.assert_called()


@pytest.mark.asyncio
async def test_order_with_received_payment_cannot_be_cancelled(service):
    order_service, repository, _ = service
    repository.get_by_id.return_value = make_order(
        status="confirmed",
        paid_amount=Decimal("100"),
        unpaid_amount=Decimal("900"),
    )

    with pytest.raises(ValueError, match="已有收款"):
        await order_service.change_status(
            SAMPLE_ORDER_ID,
            "cancelled",
            reason="客户取消",
            operated_by=uuid4(),
        )

    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_cancellation_closes_all_open_delivery_tasks(service):
    order_service, repository, db = service
    order = make_order(status="in_installation")
    repository.get_by_id.return_value = order

    design_task = MagicMock(status="confirmed")
    production_task = MagicMock(status="in_progress")
    installation_task = MagicMock(status="pending_acceptance")
    acceptance = MagicMock(status="pending", deleted_at=None)
    task_results = []
    for tasks in (
        [design_task],
        [production_task],
        [installation_task],
        [acceptance],
    ):
        result = MagicMock()
        result.scalars.return_value.all.return_value = tasks
        task_results.append(result)
    db.execute.side_effect = task_results
    db.flush = AsyncMock()

    result = await order_service.change_status(
        SAMPLE_ORDER_ID,
        "cancelled",
        reason="客户取消",
        operated_by=uuid4(),
    )

    assert result["status"] == "cancelled"
    assert design_task.status == "confirmed"
    assert production_task.status == "cancelled"
    assert installation_task.status == "cancelled"
    assert acceptance.deleted_at is not None
    assert order.deleted_at is not None


@pytest.mark.asyncio
async def test_list_orders(service):
    order_service, repository, _ = service
    repository.list_all.return_value = ([make_order()], 1)

    orders, total = await order_service.list_all(1, 20)

    assert total == 1
    assert orders[0]["order_no"] == "O20260629-0001"
    repository.list_all.assert_awaited_once_with(
        skip=0,
        limit=20,
        status=None,
        customer_id=None,
        keyword=None,
        exclude_status=None,
    )


@pytest.mark.asyncio
async def test_get_order(service):
    order_service, repository, _ = service
    repository.get_by_id.return_value = make_order()

    order = await order_service.get_by_id(SAMPLE_ORDER_ID)

    assert order["project_name"] == "测试订单"
    assert order["status"] == "pending_confirm"


@pytest.mark.asyncio
async def test_get_missing_order(service):
    order_service, repository, _ = service
    repository.get_by_id.return_value = None

    assert await order_service.get_by_id(SAMPLE_ORDER_ID) is None


@pytest.mark.asyncio
async def test_set_order_cost(service):
    order_service, repository, _ = service
    repository.get_by_id.return_value = make_order(total_amount=Decimal("5000"))

    order = await order_service.set_cost(SAMPLE_ORDER_ID, 3000)

    assert order["cost_amount"] == 3000
    assert order["gross_profit"] == 2000


@pytest.mark.asyncio
async def test_set_cost_rejects_quote(service):
    order_service, repository, _ = service
    repository.get_by_id.return_value = make_order(doc_type="quote")

    with pytest.raises(ValueError, match="仅订单可设置成本"):
        await order_service.set_cost(SAMPLE_ORDER_ID, 100)


@pytest.mark.asyncio
async def test_auto_calculate_cost(service):
    order_service, repository, db = service
    repository.get_by_id.return_value = make_order(total_amount=Decimal("10000"))
    outsource = MagicMock()
    outsource.scalar.return_value = 2000
    inventory = MagicMock()
    inventory.scalar.return_value = 1500
    project_cost = MagicMock()
    project_cost.scalar.return_value = 500
    db.execute.side_effect = [outsource, inventory, project_cost]

    order = await order_service.auto_calculate_cost(SAMPLE_ORDER_ID)

    assert order["cost_amount"] == 4000
    assert order["gross_profit"] == 6000


# ─────────────────────────────────────────────
# 订单保存 → 自动同步关联框架合同项目的 项目名称/部门
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_update_syncs_linked_framework_contract_projects():
    """订单保存后，关联框架合同项目的 项目名称/部门 同步为订单最新值（金额不覆盖）。"""
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    doc = make_order(project_name="奖牌制作", department="督察科")
    project1 = MagicMock(project_name="奖牌制作", department="监管科")
    project2 = MagicMock(project_name="奖牌制作", department="政治部人事科")

    outsource_result = MagicMock()
    outsource_result.scalars.return_value.all.return_value = []
    projects_result = MagicMock()
    projects_result.scalars.return_value.all.return_value = [project1, project2]
    db.execute = AsyncMock(side_effect=[outsource_result, projects_result])
    db.flush = AsyncMock()

    service = BusinessDocumentService(db, doc_type="order")
    service.repo.get_by_id = AsyncMock(return_value=doc)
    service.repo.update = AsyncMock(side_effect=lambda d, data: d)
    service._sync_contact_to_customer = AsyncMock()
    service._to_detail = MagicMock(return_value={})

    await service.update(doc.id, {"project_name": "奖牌制作", "department": "督察科"})

    assert project1.project_name == "奖牌制作"
    assert project1.department == "督察科"
    assert project2.department == "督察科"
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_order_update_skips_sync_when_no_linked_project():
    """订单无关联框架合同项目时，同步静默跳过，不抛错。"""
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    doc = make_order(project_name="奖牌制作", department="督察科")

    outsource_result = MagicMock()
    outsource_result.scalars.return_value.all.return_value = []
    projects_result = MagicMock()
    projects_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[outsource_result, projects_result])
    db.flush = AsyncMock()

    service = BusinessDocumentService(db, doc_type="order")
    service.repo.get_by_id = AsyncMock(return_value=doc)
    service.repo.update = AsyncMock(side_effect=lambda d, data: d)
    service._sync_contact_to_customer = AsyncMock()
    service._to_detail = MagicMock(return_value={})

    await service.update(doc.id, {"project_name": "奖牌制作", "department": "督察科"})

    db.flush.assert_not_awaited()
