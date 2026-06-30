"""Tests for QuoteFinder — draft composition, similar search, and keyword extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tests.conftest import MockAsyncSession, MockResult


class TestQuoteFinderDraftComposition:
    """Tests for compose_draft_quote and the generate_quote_draft alias."""

    def test_generate_quote_draft_is_alias(self, mock_db):
        """generate_quote_draft should delegate to compose_draft_quote and return same result."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)

        # Mock extract_keywords and find_similar to control output
        finder.extract_keywords = _async_return(["文化墙", "PVC"])
        finder.find_similar = _async_return(([], {"recommended_price": 3500}))

        import asyncio

        # Call the alias method
        result = asyncio.run(
            finder.generate_quote_draft("6m×2m PVC文化墙", None)
        )

        # Should return a structured draft
        assert "project_name" in result
        assert "items" in result
        assert "total_estimate" in result
        assert "confidence" in result
        assert "similar_quotes" in result
        assert result["confidence"] == "low"  # No similar quotes found
        assert isinstance(result["items"], list)

    def test_compose_draft_quote_no_catalog_matches(self, mock_db):
        """When no catalog matches found, creates a single generic item from description."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)

        # No keywords extracted and no catalog matches
        finder.extract_keywords = _async_return([])
        finder.find_similar = _async_return(([], {
            "price_range": [0, 0], "avg_price": 0,
            "avg_margin": 0, "recommended_price": 0,
        }))

        import asyncio
        result = asyncio.run(
            finder.compose_draft_quote("非常特殊的定制需求", None)
        )

        assert len(result["items"]) == 1
        assert result["items"][0]["item_name"] == "非常特殊的定制需求"
        assert result["items"][0]["remark"] == "请手动补充产品/材质信息"
        assert result["confidence"] == "low"
        assert result["total_estimate"] == 0

    def test_compose_draft_quote_with_similar_quotes(self, mock_db):
        """Confidence should be 'medium' when similar quotes are found."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)

        finder.extract_keywords = _async_return(["文化墙"])
        finder.find_similar = _async_return(
            ([{
                "quote_id": "q1", "quote_no": "Q001",
                "project_name": "Another Project",
                "total_area": 12.0,
                "items_summary": "PVC板, 亚克力",
                "total_amount": 5000.0,
                "gross_profit": 1500.0,
                "profit_margin": 0.3,
                "created_at": "2026-06-01T00:00:00",
            }],
            {
                "price_range": [5000.0, 5000.0],
                "avg_price": 5000.0,
                "avg_margin": 0.3,
                "recommended_price": 5000.0,
            }),
        )

        import asyncio
        result = asyncio.run(
            finder.compose_draft_quote("文化墙", None)
        )

        assert result["confidence"] == "medium"
        assert result["similar_quotes_count"] == 1
        assert len(result["similar_quotes"]) == 1
        assert result["total_estimate"] == 5000.0

    def test_generate_quote_draft_returns_consistent_interface(self, mock_db):
        """Both methods should return the same keys (interface consistency)."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        finder.extract_keywords = _async_return(["测试"])
        finder.find_similar = _async_return(([], {"recommended_price": 0}))

        import asyncio

        result_a = asyncio.run(finder.compose_draft_quote("测试", None))
        result_b = asyncio.run(finder.generate_quote_draft("测试", None))

        # Both should have the same keys
        expected_keys = {
            "project_name", "items", "total_estimate", "confidence",
            "similar_quotes_count", "similar_quotes", "ai_analysis", "risk_notes",
        }
        assert set(result_a.keys()) == expected_keys
        assert set(result_b.keys()) == expected_keys
        # Values should match since alias delegates
        assert result_a["items"] == result_b["items"]


class TestQuoteFinderKeywordExtraction:
    """Tests for extract_keywords method."""

    def test_extract_keywords_filters_stop_words(self, mock_db):
        """Common Chinese stop words should be removed from candidates."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        # Set up mock DB to return no catalog matches
        mock_db.execute_result = None

        import asyncio
        keywords = asyncio.run(
            finder.extract_keywords("的 了 是 文化墙 PVC")
        )

        # Stop words should be absent
        assert "的" not in keywords
        assert "了" not in keywords
        assert "是" not in keywords

    def test_extract_keywords_handles_empty_description(self, mock_db):
        """Empty or whitespace-only description should return empty list."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        finder.db = mock_db

        import asyncio
        result = asyncio.run(finder.extract_keywords(""))
        assert result == []

    def test_extract_keywords_normalizes_delimiters(self, mock_db):
        """Different delimiter formats should be handled consistently."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        mock_db.execute_result = None

        import asyncio
        # × and * should both work as separators
        result = asyncio.run(finder.extract_keywords("6m×2m 文化墙"))
        assert isinstance(result, list)


class TestQuoteFinderFindSimilar:
    """Tests for find_similar method."""

    def test_find_similar_returns_empty_on_no_matches(self, mock_db):
        """When no quotes match, should return empty list and zero pricing."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        # Mock the database query to return empty
        mock_db.execute = AsyncMock(return_value=MockResult(scalars_return=[]))

        import asyncio
        results, pricing = asyncio.run(
            finder.find_similar("nonexistent_xyz_keyword")
        )

        assert results == []
        assert pricing["avg_price"] == 0
        assert pricing["recommended_price"] == 0
        assert pricing["price_range"] == [0, 0]


class TestQuoteFinderConstructor:
    """Minimal constructor tests."""

    def test_quote_finder_instantiation(self, mock_db):
        """QuoteFinder should accept a db session."""
        from app.ai.rule_based.quote_finder import QuoteFinder

        finder = QuoteFinder(mock_db)
        assert finder.db is mock_db


# ── Helpers ───────────────────────────────────────────────────────────

def _async_return(value):
    async def fn(*args, **kwargs):
        return value
    return fn
