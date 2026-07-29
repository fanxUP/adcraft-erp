from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.order_customer_service import ensure_document_customer


@pytest.mark.asyncio
async def test_free_text_customer_is_promoted_when_quote_becomes_order():
    db = MagicMock()
    db.flush = AsyncMock()
    document = MagicMock(
        customer_id=None,
        customer_name="临时客户",
        contact_person="张经理",
        contact_phone="13800000000",
        doc_no="Q20260730-0001",
    )
    customer = MagicMock(id=uuid4())
    contact = MagicMock()

    with patch(
        "app.models.customer.Customer",
        return_value=customer,
    ) as customer_class, patch(
        "app.models.customer.CustomerContact",
        return_value=contact,
    ) as contact_class, patch(
        "app.services.number_generator.generate_customer_no",
        AsyncMock(return_value="C20260730-0001"),
    ):
        await ensure_document_customer(db, document, uuid4())

    assert document.customer_id == customer.id
    customer_class.assert_called_once()
    contact_class.assert_called_once_with(
        customer_id=customer.id,
        name="张经理",
        phone="13800000000",
        is_primary=True,
    )
    assert db.add.call_count == 2


@pytest.mark.asyncio
async def test_quote_without_any_customer_cannot_be_converted():
    document = MagicMock(customer_id=None, customer_name="  ")

    with pytest.raises(ValueError, match="报价缺少客户"):
        await ensure_document_customer(MagicMock(), document, uuid4())
