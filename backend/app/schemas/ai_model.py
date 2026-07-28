"""Pydantic schemas for AI Model management."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIModelCreate(BaseModel):
    provider_id: str = Field(..., description="Provider UUID")
    upstream_model_code: str = Field(..., min_length=1, max_length=300, description="Actual model name on provider")
    display_name: str = Field(..., max_length=200, description="User-friendly display name")
    model_role: Optional[str] = Field(None, description="fast / standard / reasoning / vision / embedding")
    model_type: str = Field("chat", description="chat / embedding / image")
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json_schema: bool = False
    supports_vision: bool = False
    supports_embedding: bool = False
    pricing: Optional[dict] = Field(None, description="Pricing configuration")
    enabled: bool = False
    priority: int = 100


class AIModelUpdate(BaseModel):
    display_name: Optional[str] = None
    model_role: Optional[str] = None
    model_type: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: Optional[bool] = None
    supports_tools: Optional[bool] = None
    supports_json_schema: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_embedding: Optional[bool] = None
    pricing: Optional[dict] = None
    declared_capabilities: Optional[dict] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AIModelResponse(BaseModel):
    id: str
    provider_id: str
    provider_name: Optional[str] = None
    upstream_model_code: str
    display_name: str
    model_role: Optional[str] = None
    model_type: str = "chat"
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json_schema: bool = False
    supports_vision: bool = False
    supports_embedding: bool = False
    pricing_json: dict = {}
    enabled: bool = False
    priority: int = 100
    health_status: str = "unknown"
    health_score: Optional[float] = None
    last_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AIModelListResponse(BaseModel):
    items: list[AIModelResponse]
    total: int
    page: int
    page_size: int
