"""Schemas for Payment Screenshot OCR (Feature 3)."""

from __future__ import annotations

from pydantic import BaseModel


class OCRExtracted(BaseModel):
    amount: float | None = None
    paid_at: str | None = None
    payer_name: str | None = None
    remark: str | None = None
    payment_method: str | None = None


class OCRRecognizeResponse(BaseModel):
    mode: str = "rule_based"  # "rule_based" or "ai_enhanced"
    image_url: str = ""
    extracted: OCRExtracted = OCRExtracted()
    confidence: str = "none"  # none / low / medium / high
    order_context: dict | None = None
