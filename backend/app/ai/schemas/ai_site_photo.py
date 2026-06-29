"""Schemas for Site Photo Recognition (Feature 2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhotoChecklist(BaseModel):
    wall_condition: str = "awaiting_review"
    height_risk: str = "awaiting_review"
    scaffolding_needed: str = "awaiting_review"
    obstacles_found: str = "awaiting_review"
    cost_impact_estimated: bool = False
    notes: str = ""


class SitePhotoAnalyzeResponse(BaseModel):
    mode: str = "rule_based"  # "rule_based" or "ai_enhanced"
    photo_url: str = ""
    checklist: PhotoChecklist = PhotoChecklist()
    ai_findings: dict | None = None
