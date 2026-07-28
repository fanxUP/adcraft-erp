"""Pydantic schemas for AI Task Route management."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Request schemas ──


class FallbackItem(BaseModel):
    provider_id: UUID
    model_role: str = "standard"


class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    rolling_window_seconds: int = 120
    open_duration_seconds: int = 60
    half_open_probe_count: int = 2


class TaskRouteCreate(BaseModel):
    task_code: str = Field(..., min_length=2, max_length=150, description="Unique task identifier")
    task_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    primary_provider_id: Optional[UUID] = None
    primary_model_role: Optional[str] = "standard"
    fallback_chain: Optional[list[FallbackItem]] = None
    required_capabilities: Optional[dict[str, bool]] = None
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    max_output_tokens: Optional[int] = Field(default=None, ge=1, le=131072)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    budget_policy_json: Optional[dict[str, Any]] = None
    data_policy_json: Optional[dict[str, Any]] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    enabled: bool = True

    @model_validator(mode="after")
    def code_no_spaces(self) -> "TaskRouteCreate":
        if " " in self.task_code:
            raise ValueError("task_code must not contain spaces")
        return self


class TaskRouteUpdate(BaseModel):
    task_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    primary_provider_id: Optional[UUID] = None
    primary_model_role: Optional[str] = None
    fallback_chain: Optional[list[FallbackItem]] = None
    required_capabilities: Optional[dict[str, bool]] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=5, le=300)
    max_output_tokens: Optional[int] = Field(default=None, ge=1, le=131072)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    budget_policy_json: Optional[dict[str, Any]] = None
    data_policy_json: Optional[dict[str, Any]] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    enabled: Optional[bool] = None


# ── Response schemas ──


class TaskRouteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    task_code: str
    task_name: str
    description: Optional[str] = None
    primary_provider_id: Optional[UUID] = None
    primary_model_role: Optional[str] = None
    fallback_chain_json: Optional[list[dict]] = None
    required_capabilities_json: Optional[dict] = None
    timeout_seconds: int
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    circuit_breaker_json: Optional[dict] = None
    enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime
