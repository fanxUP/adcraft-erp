"""Schemas for Smart Business Reports (Feature 4)."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BusinessNarrativeResponse(BaseModel):
    mode: str = "rule_based"  # "rule_based" or "ai_enhanced"
    period: str = "monthly"  # weekly / monthly
    year: int = 0
    month: int | None = None
    week: int | None = None
    stats: dict[str, Any] = {}
    narrative: str = ""
    suggestions: list[str] = []
