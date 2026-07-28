"""普通报价与 CDR 智能报价隔离的回归测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business_document import BusinessDocument
from app.services.cdr_quote_service import CdrQuoteService


def test_business_document_declares_quote_mode():
    assert "quote_mode" in BusinessDocument.__table__.columns


@pytest.mark.asyncio
async def test_cdr_quote_list_only_queries_cdr_mode():
    db = MagicMock()

    with patch(
        "app.services.cdr_quote_service.BusinessDocumentService",
        create=True,
    ):
        service = CdrQuoteService(db)

    with patch(
        "app.services.business_document_service.BusinessDocumentService"
    ) as service_class:
        document_service = service_class.return_value
        document_service.repo.list_all = AsyncMock(return_value=([], 0))

        items, total = await service.list_quotes()

    assert items == []
    assert total == 0
    service_class.assert_called_once_with(
        db,
        doc_type="quote",
        quote_mode="cdr",
    )
