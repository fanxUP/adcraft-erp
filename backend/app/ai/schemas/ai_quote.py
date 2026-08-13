"""Schemas for AI Quote Assistant (Feature 1)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AIQuoteAssistRequest(BaseModel):
    description: str = Field(..., min_length=5, description="自然语言描述的需求")
    customer_id: str | None = Field(None, description="关联客户ID")


class DraftQuoteItem(BaseModel):
    item_name: str
    width: float | None = None
    height: float | None = None
    quantity: float = 1
    unit: str = "㎡"
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    material_process: str | None = None
    unit_price: float | None = None
    other_fee: float = 0
    subtotal: float = 0
    remark: str = ""


class SimilarQuoteItem(BaseModel):
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


class AIQuoteAssistResponse(BaseModel):
    mode: str  # "rule_based" or "ai_enhanced"
    project_name: str = ""
    items: list[DraftQuoteItem] = []
    total_estimate: float = 0
    confidence: str = "low"  # low / medium / high
    similar_quotes_count: int = 0
    similar_quotes: list[SimilarQuoteItem] = []
    ai_analysis: str = ""
    risk_notes: list[str] = []
