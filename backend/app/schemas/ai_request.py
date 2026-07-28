"""Pydantic schemas for AI request logging and querying."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AIRequestResponse(BaseModel):
    id: UUID
    request_id: str
    tenant_id: UUID
    user_id: Optional[UUID] = None
    task_code: str
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    model_code: Optional[str] = None
    business_object_type: Optional[str] = None
    business_object_id: Optional[UUID] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    status: str
    attempt_count: int
    fallback_count: int
    latency_ms: Optional[int] = None
    first_token_latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    currency: Optional[str] = None
    error_code: Optional[str] = None
    error_message_sanitized: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class UsageDailyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    usage_date: str
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    task_code: Optional[str] = None
    request_count: int
    success_count: int
    failed_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    currency: Optional[str] = None
    avg_latency_ms: Optional[float] = None
