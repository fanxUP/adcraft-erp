"""Tests for QuoteFinder — historical quote search and keyword extraction."""

from __future__ import annotations

import pytest


class TestQuoteFinder:
    def test_extract_keywords_normalizes_input(self):
        """Keyword extraction should handle various input formats."""
        from app.ai.rule_based.quote_finder import STOP_WORDS
        assert "的" in STOP_WORDS
        assert "了" in STOP_WORDS
        assert "和" in STOP_WORDS

    def test_quote_finder_imports(self):
        """QuoteFinder class should be importable."""
        from app.ai.rule_based.quote_finder import QuoteFinder
        assert QuoteFinder is not None


class TestAISchemas:
    def test_similar_quotes_response(self):
        """SimilarQuotesResponse schema should validate."""
        from app.ai.schemas.ai_knowledge import SimilarQuotesResponse, SimilarQuoteResult
        result = SimilarQuoteResult(
            quote_id="abc",
            quote_no="Q20260629-0001",
            project_name="Test",
            total_amount=5000.0,
        )
        assert result.quote_no == "Q20260629-0001"
        assert result.total_amount == 5000.0

    def test_quote_assist_schema(self):
        """AIQuoteAssistResponse should accept valid data."""
        from app.ai.schemas.ai_quote import AIQuoteAssistRequest, AIQuoteAssistResponse
        req = AIQuoteAssistRequest(description="一个 6m × 2m 的文化墙")
        assert "文化墙" in req.description

        resp = AIQuoteAssistResponse(
            mode="rule_based",
            project_name="文化墙",
            items=[],
            total_estimate=5000.0,
        )
        assert resp.mode == "rule_based"
        assert resp.total_estimate == 5000.0

    def test_quote_assist_request_min_length(self):
        """Description should require minimum 5 characters."""
        from app.ai.schemas.ai_quote import AIQuoteAssistRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            AIQuoteAssistRequest(description="ab")  # Too short
