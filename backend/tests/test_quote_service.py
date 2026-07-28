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
        "items": [],
        "status_logs": [],
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(quote, key, value)
    return quote


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
    repository.get_by_id.return_value = make_quote(status="draft")

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
async def test_calculate_quote_amount(service):
    quote_service, repository = service
    item = MagicMock()
    item.length = Decimal("2")
    item.width = Decimal("3")
    item.quantity = Decimal("1")
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

    assert quote.subtotal_amount == Decimal("630")
    assert quote.total_amount == Decimal("630")
