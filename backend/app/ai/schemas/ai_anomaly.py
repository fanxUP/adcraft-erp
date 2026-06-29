"""Schemas for Smart Anomaly Alerts (Feature 5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalyAlert(BaseModel):
    type: str = Field(..., description="Anomaly type code")
    severity: str = Field(..., description="critical / warning / info")
    object_type: str = Field(..., description="Source entity type")
    object_id: str = Field(..., description="Source entity ID")
    title: str = ""
    detail: str = ""
    created_at: str = ""


class AnomalySummary(BaseModel):
    critical: int = 0
    warning: int = 0
    info: int = 0


class AnomalyScanResponse(BaseModel):
    mode: str = "rule_based"
    alerts: list[AnomalyAlert] = []
    summary: AnomalySummary = AnomalySummary()
