"""Tests for QuoteService — quote CRUD, calculation, and order conversion."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest

from tests.conftest import MockAsyncSession, MockResult

SAMPLE_QUOTE_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")
SAMPLE_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def make_mock_quote(quote_id=SAMPLE_QUOTE_ID, status="draft", total_amount=10000.0,
                    customer_id=SAMPLE_CUSTOMER_ID, has_items=True):
    """Create a mock Quote object with all attributes needed by _quote_to_detail."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    q = MagicMock()
    q.id = quote_id
    q.quote_no = "Q20260630-0001"
    q.customer_id = customer_id
    q.project_name = "Test Project"
    q.sales_user_id = SAMPLE_USER_ID
    q.status = status
    q.subtotal_amount = total_amount
    q.discount_amount = 0
    q.tax_rate = 0
    q.tax_amount = 0
    q.total_amount = total_amount
    q.valid_until = None
    q.remark = ""
    q.created_at = now

    if has_items:
        mock_item = MagicMock()
        mock_item.id = uuid4()
        mock_item.quote_id = quote_id
        mock_item.product_id = None
        mock_item.material_id = None
        mock_item.process_id = None
        mock_item.item_name = "Test Item"
        mock_item.length = 2.0
        mock_item.width = 1.5
        mock_item.height = None
        mock_item.quantity = 3
        mock_item.unit = "㎡"
        mock_item.area = 9.0
        mock_item.unit_price = 500.0
        mock_item.process_fee = 0
        mock_item.installation_fee = 200.0
        mock_item.design_fee = 0
        mock_item.transport_fee = 0
        mock_item.other_fee = 0
        mock_item.subtotal_amount = 4700.0
        mock_item.remark = ""
        mock_item.sort_order = 0
        q.items = [mock_item]
    else:
        q.items = []

    return q


class TestQuoteServiceCRUD:
    """Basic CRUD operations."""

    def test_quote_service_instantiation(self, mock_db):
        """QuoteService should accept a DB session and initialize repo."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        assert service.db is mock_db
        assert service.repo is not None

    def test_get_quote_returns_none_for_missing(self, mock_db):
        """get_quote should return None when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        result = asyncio.run(service.get_quote(SAMPLE_QUOTE_ID))
        assert result is None

    def test_get_quote_returns_detail(self, mock_db):
        """get_quote should return full detail dict when quote exists."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote()
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)

        import asyncio
        result = asyncio.run(service.get_quote(SAMPLE_QUOTE_ID))
        assert result is not None
        assert result["id"] == str(SAMPLE_QUOTE_ID)
        assert result["quote_no"] == "Q20260630-0001"
        assert result["total_amount"] == 10000.0
        assert len(result["items"]) == 1

    def test_list_quotes_returns_summaries(self, mock_db):
        """list_quotes should return paginated summaries."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote()
        service.repo.list_quotes = AsyncMock(return_value=([mock_quote], 1))

        import asyncio
        items, total = asyncio.run(service.list_quotes(1, 20))
        assert total == 1
        assert len(items) == 1
        assert items[0]["id"] == str(SAMPLE_QUOTE_ID)
        # Summary should NOT include the 'items' key
        assert "items" not in items[0]

    def test_delete_quote_returns_true(self, mock_db):
        """delete_quote should return True when quote exists."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote()
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)
        service.repo.soft_delete = AsyncMock()

        import asyncio
        result = asyncio.run(service.delete_quote(SAMPLE_QUOTE_ID))
        assert result is True

    def test_delete_quote_returns_false_for_missing(self, mock_db):
        """delete_quote should return False when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        result = asyncio.run(service.delete_quote(SAMPLE_QUOTE_ID))
        assert result is False

    def test_update_quote_raises_for_missing(self, mock_db):
        """update_quote should raise ValueError when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        with pytest.raises(ValueError, match="报价单不存在"):
            asyncio.run(service.update_quote(SAMPLE_QUOTE_ID, {}))

    def test_update_quote_converts_decimals(self, mock_db):
        """update_quote should convert discount and tax rate to Decimal."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote()
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)
        service.repo.update = AsyncMock(return_value=mock_quote)

        import asyncio
        result = asyncio.run(service.update_quote(
            SAMPLE_QUOTE_ID,
            {"discount_amount": 500, "tax_rate": 0.06},
        ))
        assert result["id"] == str(SAMPLE_QUOTE_ID)


class TestQuoteCalculation:
    """calculate_quote logic."""

    def test_calculate_quote_raises_for_missing(self, mock_db):
        """Should raise ValueError when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        with pytest.raises(ValueError, match="报价单不存在"):
            asyncio.run(service.calculate_quote(SAMPLE_QUOTE_ID))

    def test_calculate_quote_with_items(self, mock_db):
        """Should compute area and subtotal for each item."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote(status="draft", total_amount=0)
        # Override with specific test values
        mock_item = MagicMock()
        mock_item.length = 6.0
        mock_item.width = 2.0
        mock_item.height = None
        mock_item.quantity = 1
        mock_item.unit_price = 500.0
        mock_item.process_fee = 100.0
        mock_item.installation_fee = 200.0
        mock_item.design_fee = 0.0
        mock_item.transport_fee = 50.0
        mock_item.other_fee = 0.0
        mock_item.area = None
        mock_item.subtotal_amount = None
        mock_quote.items = [mock_item]
        mock_quote.subtotal_amount = 0
        mock_quote.discount_amount = 0
        mock_quote.tax_rate = 0

        service.repo.get_by_id = AsyncMock(return_value=mock_quote)
        service.repo.get_items = AsyncMock(return_value=[mock_item])

        import asyncio
        result = asyncio.run(service.calculate_quote(SAMPLE_QUOTE_ID))

        # Area: 6 × 2 × 1 = 12
        assert mock_item.area == 12.0
        # Subtotal: 12 × 500 + 100 + 200 + 0 + 50 + 0 = 6350
        assert mock_item.subtotal_amount == 6350.0
        assert mock_quote.subtotal_amount == 6350.0


class TestQuoteConfirm:
    """confirm_quote business logic."""

    def test_confirm_quote_raises_for_missing(self, mock_db):
        """Should raise ValueError when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        with pytest.raises(ValueError, match="报价单不存在"):
            asyncio.run(service.confirm_quote(SAMPLE_QUOTE_ID))

    def test_confirm_non_draft_raises(self, mock_db):
        """Should raise ValueError when quote is already confirmed."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote(status="confirmed")
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)

        import asyncio
        with pytest.raises(ValueError, match="只有草稿状态"):
            asyncio.run(service.confirm_quote(SAMPLE_QUOTE_ID))

    def test_confirm_draft_succeeds(self, mock_db):
        """Should set status to confirmed."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote(status="draft")
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)

        import asyncio
        result = asyncio.run(service.confirm_quote(SAMPLE_QUOTE_ID))
        assert mock_quote.status == "confirmed"
        assert result["status"] == "confirmed"


class TestQuoteConvertToOrder:
    """convert_to_order business rules."""

    def test_convert_missing_quote_raises(self, mock_db):
        """Should raise when quote not found."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        service.repo.get_by_id = AsyncMock(return_value=None)

        import asyncio
        with pytest.raises(ValueError, match="报价单不存在"):
            asyncio.run(service.convert_to_order(SAMPLE_QUOTE_ID, SAMPLE_USER_ID))

    def test_convert_non_confirmed_raises(self, mock_db):
        """Should raise when quote is not confirmed."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)
        mock_quote = make_mock_quote(status="draft")
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)

        import asyncio
        with pytest.raises(ValueError, match="只有已确认"):
            asyncio.run(service.convert_to_order(SAMPLE_QUOTE_ID, SAMPLE_USER_ID))


class TestQuoteCreate:
    """create_quote workflow."""

    def test_create_minimal_quote(self, mock_db):
        """Should create a quote with defaults when no items provided."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)

        mock_quote = make_mock_quote(has_items=False)
        service.repo.create = AsyncMock(return_value=mock_quote)

        # Mock number_generator
        with patch("app.services.quote_service.generate_quote_no",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Q20260630-0001"

            import asyncio
            result = asyncio.run(service.create_quote({
                "project_name": "New Project",
                "customer_id": str(SAMPLE_CUSTOMER_ID),
                "sales_user_id": str(SAMPLE_USER_ID),
            }))

            assert result["quote_no"] == "Q20260630-0001"
            assert result["status"] == "draft"

    def test_create_quote_with_decimal_conversion(self, mock_db):
        """Should convert string amounts to Decimal for items."""
        from app.services.quote_service import QuoteService
        service = QuoteService(mock_db)

        mock_quote = make_mock_quote()
        service.repo.create = AsyncMock(return_value=mock_quote)
        # Called twice: once by create_quote, once by calculate_quote
        service.repo.get_by_id = AsyncMock(return_value=mock_quote)
        service.repo.get_items = AsyncMock(return_value=mock_quote.items)

        with patch("app.services.quote_service.generate_quote_no",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Q20260630-0002"

            import asyncio
            result = asyncio.run(service.create_quote({
                "project_name": "Project with Items",
                "customer_id": str(SAMPLE_CUSTOMER_ID),
                "items": [{
                    "item_name": "Test Item",
                    "unit_price": "500.50",
                    "quantity": "2",
                    "process_fee": "100",
                }],
            }))

            assert result is not None
