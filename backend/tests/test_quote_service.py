"""统一业务单据服务的报价路径回归测试。"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.services.business_document_service import BusinessDocumentService

SAMPLE_QUOTE_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")


def make_quote(**overrides):
    now = datetime.now(timezone.utc)
    quote = MagicMock()
    defaults = {
        "id": SAMPLE_QUOTE_ID,
        "doc_type": "quote",
        "doc_no": "Q20260630-0001",
        "customer_id": SAMPLE_CUSTOMER_ID,
        "customer_name": None,
        "customer": None,
        "project_name": "测试报价",
        "sales_user_id": None,
        "status": "draft",
        "quote_mode": "regular",
        "subtotal_amount": Decimal("1000"),
        "discount_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "total_amount": Decimal("1000"),
        "valid_until": None,
        "remark": None,
        "department": None,
        "contact_person": None,
        "contact_phone": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
        "source_quote_id": None,
        "paid_amount": Decimal("0"),
        "unpaid_amount": Decimal("0"),
        "cost_amount": Decimal("0"),
        "gross_profit": Decimal("0"),
        "delivery_deadline": None,
        "installation_address": None,
        "items": [],
        "status_logs": [],
        "design_tasks": [],
        "production_tasks": [],
        "installation_tasks": [],
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(quote, key, value)
    return quote


def make_quote_item(**overrides):
    item = MagicMock()
    defaults = {
        "id": uuid4(),
        "item_name": "测试明细",
        "product_id": None,
        "material_id": None,
        "process_id": None,
        "length": None,
        "length_unit": None,
        "width": None,
        "width_unit": "m",
        "height": None,
        "height_unit": "m",
        "quantity": Decimal("1"),
        "unit": "项",
        "use_area": False,
        "quantity_mode": "piece",
        "pieces": Decimal("1"),
        "area": Decimal("0"),
        "unit_price": Decimal("100"),
        "process_fee": Decimal("0"),
        "installation_fee": Decimal("0"),
        "design_fee": Decimal("0"),
        "transport_fee": Decimal("0"),
        "other_fee": Decimal("0"),
        "subtotal_amount": Decimal("100"),
        "remark": None,
        "image_url": None,
        "sort_order": 0,
        "group_name": None,
        "material_process": None,
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(item, key, value)
    return item


@pytest.fixture
def service():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    with patch(
        "app.services.business_document_service.BusinessDocumentRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.get_by_id = AsyncMock()
        repository.list_all = AsyncMock(return_value=([], 0))
        repository.get_items = AsyncMock(return_value=[])
        repository.get_item = AsyncMock()
        repository.update_item = AsyncMock()
        repository.delete_item = AsyncMock()
        repository.get_next_version_no = AsyncMock(return_value=1)
        repository.create_version = AsyncMock()

        async def update(document, data):
            for key, value in data.items():
                setattr(document, key, value)
            return document

        repository.update = AsyncMock(side_effect=update)
        repository.create_status_log = AsyncMock()
        yield BusinessDocumentService(db, doc_type="quote"), repository


@pytest.mark.asyncio
async def test_list_quotes_exposes_quote_number(service):
    quote_service, repository = service
    repository.list_all.return_value = ([make_quote()], 1)

    quotes, total = await quote_service.list_all(1, 20)

    assert total == 1
    assert quotes[0]["quote_no"] == "Q20260630-0001"


@pytest.mark.asyncio
async def test_get_quote_detail(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote()

    quote = await quote_service.get_by_id(SAMPLE_QUOTE_ID)

    assert quote["quote_no"] == "Q20260630-0001"
    assert quote["project_name"] == "测试报价"


@pytest.mark.asyncio
async def test_get_missing_quote(service):
    quote_service, repository = service
    repository.get_by_id.return_value = None

    assert await quote_service.get_by_id(SAMPLE_QUOTE_ID) is None


@pytest.mark.asyncio
async def test_quote_status_transition(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote(
        status="draft",
        items=[make_quote_item()],
    )

    quote = await quote_service.change_status(
        SAMPLE_QUOTE_ID, "confirmed", None, uuid4()
    )

    assert quote["status"] == "confirmed"


@pytest.mark.asyncio
async def test_quote_rejects_invalid_status_transition(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote(status="draft")

    with pytest.raises(ValueError, match="不允许"):
        await quote_service.change_status(
            SAMPLE_QUOTE_ID, "converted", None, uuid4()
        )


@pytest.mark.asyncio
async def test_quote_cannot_be_confirmed_without_items(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote(status="draft", items=[])

    with pytest.raises(ValueError, match="请先添加报价明细"):
        await quote_service.change_status(
            SAMPLE_QUOTE_ID,
            "confirmed",
            None,
            uuid4(),
        )


@pytest.mark.asyncio
async def test_confirmed_quote_cannot_be_edited(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote(status="confirmed")

    with pytest.raises(ValueError, match="仅草稿报价可以编辑"):
        await quote_service.update(
            SAMPLE_QUOTE_ID,
            {"project_name": "绕过前端修改"},
        )

    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_draft_quote_can_switch_to_free_text_customer(service):
    quote_service, repository = service
    quote = make_quote(
        status="draft",
        customer_id=uuid4(),
        customer_name=None,
    )
    repository.get_by_id.return_value = quote

    await quote_service.update(
        SAMPLE_QUOTE_ID,
        {"customer_name": "新客户名称"},
    )

    assert quote.customer_id is None
    assert quote.customer_name == "新客户名称"


@pytest.mark.asyncio
async def test_quote_item_must_belong_to_quote(service):
    quote_service, repository = service
    repository.get_by_id.return_value = make_quote(status="draft")
    repository.get_item.return_value = None

    with pytest.raises(ValueError, match="不属于当前报价"):
        await quote_service.update_item(
            SAMPLE_QUOTE_ID,
            uuid4(),
            {"unit_price": 100},
        )

    repository.update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_convert_quote_initializes_order_receivable(service):
    quote_service, repository = service
    quote = make_quote(
        status="confirmed",
        total_amount=Decimal("1680.50"),
    )
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = quote
    quote_service.db.execute.return_value = execute_result

    with patch(
        "app.services.number_generator.generate_order_no",
        AsyncMock(return_value="O20260730-0001"),
    ):
        order = await quote_service.convert_doc_type(
            SAMPLE_QUOTE_ID,
            "order",
            uuid4(),
        )

    assert order["paid_amount"] == 0
    assert order["unpaid_amount"] == 1680.5
    assert order["gross_profit"] == 1680.5
    assert quote.doc_type == "order"
    repository.create_version.assert_awaited_once()


@pytest.mark.asyncio
async def test_calculate_quote_amount(service):
    quote_service, repository = service
    item = MagicMock()
    item.width = Decimal("2")
    item.width_unit = "m"
    item.height = Decimal("3")
    item.height_unit = "m"
    item.pieces = Decimal("1")
    item.quantity = Decimal("1")
    item.use_area = True
    item.unit_price = Decimal("100")
    item.process_fee = Decimal("10")
    item.installation_fee = Decimal("20")
    item.design_fee = Decimal("0")
    item.transport_fee = Decimal("0")
    item.other_fee = Decimal("0")
    item.subtotal_amount = Decimal("630")
    quote = make_quote(
        subtotal_amount=Decimal("0"),
        discount_amount=Decimal("0"),
        tax_rate=Decimal("0"),
    )
    repository.get_by_id.return_value = quote
    repository.get_items.return_value = [item]

    await quote_service._calculate_quote(SAMPLE_QUOTE_ID)

    assert quote.subtotal_amount == Decimal("600")
    assert quote.total_amount == Decimal("600")
