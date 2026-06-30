"""Schemas for Quote Knowledge Base (Feature 6)."""

from __future__ import annotations

from pydantic import BaseModel


class SimilarQuoteResult(BaseModel):
    quote_id: str
    quote_no: str
    project_name: str
    total_area: float | None = None
    items_summary: str = ""
    total_amount: float = 0
    gross_profit: float | None = None
    profit_margin: float | None = None
    created_at: str | None = None


class PricingSummary(BaseModel):
    price_range: list[float] = []
    avg_price: float = 0
    avg_margin: float = 0
    recommended_price: float = 0


class SimilarQuotesResponse(BaseModel):
    mode: str = "rule_based"
    items: list[SimilarQuoteResult] = []
    pricing_summary: PricingSummary = PricingSummary()
