"""Regression tests for one automatic task card per order stage."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.customer import Customer  # noqa: F401 - register vehicle relationships
from app.models.user import User  # noqa: F401 - register task FK mappers
from app.models.vehicle import Vehicle  # noqa: F401 - register polymorphic attachment mapper
from app.services.business_document_service import BusinessDocumentService
from app.services.task_service import (
    _create_installation_task_for_item,
    _create_production_task_for_item,
    _new_unstarted_item_state,
)


ORDER_ID = UUID("33333333-3333-3333-3333-333333333333")
CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")
ITEM_ONE_ID = UUID("55555555-5555-5555-5555-555555555555")
ITEM_TWO_ID = UUID("66666666-6666-6666-6666-666666666666")


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


def _item(item_id: UUID):
    item = MagicMock()
    item.id = item_id
    item.lifecycle_status = "active"
    item.material_id = None
    item.process_id = None
    item.length = None
    item.width = None
    item.height = None
    item.quantity = 1
    return item


def _order(items):
    order = MagicMock()
    order.id = ORDER_ID
    order.customer_id = CUSTOMER_ID
    order.project_name = "测试项目"
    order.items = items
    order.installation_address = "测试地址"
    order.contact_person = "联系人"
    order.contact_phone = "13800000000"
    return order


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "task_type", "model_name", "number_name"),
    [
        ("_auto_create_design_task", "design", "DesignTask", "D20260909-0001"),
        ("_auto_create_production_task", "production", "ProductionTask", "P20260909-0001"),
        ("_auto_create_installation_task", "installation", "InstallationTask", "I20260909-0001"),
    ],
)
async def test_auto_stage_task_creates_one_task_and_links_all_active_items(
    method_name,
    task_type,
    model_name,
    number_name,
):
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult([]))
    db.flush = AsyncMock()
    db.add = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    items = [_item(ITEM_ONE_ID), _item(ITEM_TWO_ID)]
    order = _order(items)

    sync_links = AsyncMock()
    generator_path = {
        "design": "app.services.number_generator.generate_design_no",
        "production": "app.services.number_generator.generate_production_no",
        "installation": "app.services.number_generator.generate_installation_no",
    }[task_type]

    with (
        patch(generator_path, new=AsyncMock(return_value=number_name)),
        patch("app.services.task_service._sync_task_order_item_links", new=sync_links),
    ):
        await getattr(service, method_name)(order)

    assert db.add.call_count == 1
    task = db.add.call_args.args[0]
    assert task.__class__.__name__ == model_name
    assert task.document_id == ORDER_ID
    assert task.order_item_id is None
    sync_links.assert_awaited_once_with(
        db,
        task_type,
        task,
        [ITEM_ONE_ID, ITEM_TWO_ID],
    )


@pytest.mark.asyncio
async def test_auto_design_task_reuses_open_card_for_a_later_order_item():
    db = MagicMock()
    existing = MagicMock(spec=DesignTask)
    existing.id = UUID("77777777-7777-7777-7777-777777777777")
    existing.document_id = ORDER_ID
    existing.order_item_id = ITEM_ONE_ID
    existing.status = "designing"
    db.execute = AsyncMock(
        side_effect=[_ScalarResult([existing]), _ScalarResult([])]
    )
    db.flush = AsyncMock()
    db.add = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    service._linked_task_item_ids = AsyncMock(return_value={ITEM_ONE_ID})
    order = _order([_item(ITEM_ONE_ID), _item(ITEM_TWO_ID)])

    sync_links = AsyncMock()
    with (
        patch("app.services.number_generator.generate_design_no", new=AsyncMock(return_value="D20260909-0002")),
        patch("app.services.task_service._sync_task_order_item_links", new=sync_links),
    ):
        await service._auto_create_design_task(order)

    db.add.assert_not_called()
    sync_links.assert_awaited_once_with(
        db,
        "design",
        existing,
        [ITEM_ONE_ID, ITEM_TWO_ID],
    )


@pytest.mark.asyncio
async def test_auto_design_task_does_not_create_a_second_card_for_an_already_linked_item():
    db = MagicMock()
    existing = MagicMock(spec=DesignTask)
    existing.id = UUID("88888888-8888-8888-8888-888888888888")
    existing.document_id = ORDER_ID
    existing.order_item_id = ITEM_ONE_ID
    existing.status = "pending"
    db.execute = AsyncMock(
        side_effect=[_ScalarResult([existing]), _ScalarResult([])]
    )
    db.flush = AsyncMock()
    db.add = MagicMock()
    service = BusinessDocumentService(db, doc_type="order")
    service._linked_task_item_ids = AsyncMock(return_value={ITEM_ONE_ID, ITEM_TWO_ID})
    order = _order([_item(ITEM_ONE_ID), _item(ITEM_TWO_ID)])

    sync_links = AsyncMock()
    with patch("app.services.task_service._sync_task_order_item_links", new=sync_links):
        await service._auto_create_design_task(order)

    db.add.assert_not_called()
    sync_links.assert_awaited_once_with(
        db,
        "design",
        existing,
        [ITEM_ONE_ID],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("creator", "task_type"),
    [
        (_create_production_task_for_item, "production"),
        (_create_installation_task_for_item, "installation"),
    ],
)
async def test_later_stage_item_reuses_open_card(creator, task_type):
    db = MagicMock()
    db.get = AsyncMock()
    order = _order([])
    item = _item(ITEM_TWO_ID)
    db.get.side_effect = [order, item]

    existing = MagicMock()
    existing.id = UUID("99999999-9999-9999-9999-999999999999")
    existing.status = "in_progress"
    db.execute = AsyncMock(return_value=_ScalarResult([existing]))
    db.flush = AsyncMock()
    db.add = MagicMock()
    source_task = MagicMock()
    source_task.document_id = ORDER_ID

    current_ids = AsyncMock(return_value=[ITEM_ONE_ID])
    by_task = AsyncMock(return_value={existing.id: [ITEM_ONE_ID]})
    sync_links = AsyncMock()
    with (
        patch("app.services.task_service._task_order_item_ids", new=current_ids),
        patch("app.services.task_service._task_item_ids_by_task", new=by_task),
        patch("app.services.task_service._sync_task_order_item_links", new=sync_links),
    ):
        await creator(db, source_task, ITEM_TWO_ID)

    db.add.assert_not_called()
    sync_links.assert_awaited_once_with(
        db,
        task_type,
        existing,
        [ITEM_ONE_ID, ITEM_TWO_ID],
    )


def test_new_item_does_not_inherit_existing_card_progress():
    task = MagicMock(status="in_progress", progress_pct=50)

    assert _new_unstarted_item_state("production", task) == ("pending", 0)
