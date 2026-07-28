"""Pydantic schemas for AI Provider management."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIProviderCreate(BaseModel):
    provider_code: str = Field(..., min_length=1, max_length=100, description="Unique code for the provider")
    provider_name: str = Field(..., min_length=1, max_length=200, description="Display name")
    provider_type: str = Field("compatible", description="official / compatible / local / custom")
    protocol: str = Field("openai_chat_completions", description="API protocol type")
    base_url: Optional[str] = Field(None, description="Base URL for API calls")
    full_url_mode: bool = Field(False, description="Use full endpoint URL instead of building from base")
    endpoint_url: Optional[str] = Field(None, description="Full endpoint URL when full_url_mode is enabled")
    api_key: Optional[str] = Field(None, description="API key (only accepted on create/update)")
    auth_header: str = Field("Authorization", description="HTTP header for auth")
    auth_prefix: Optional[str] = Field("Bearer", description="Auth header prefix")
    custom_headers: Optional[dict] = Field(None, description="Additional HTTP headers")
    proxy_config: Optional[dict] = Field(None, description="Proxy configuration")
    timeout_seconds: int = Field(60, ge=5, le=300, description="Request timeout")
    retry_count: int = Field(2, ge=0, le=10, description="Number of retries")
    tls_verify: bool = Field(True, description="Verify TLS certificates")
    enabled: bool = Field(False, description="Whether provider is enabled")
    priority: int = Field(100, ge=0, le=9999, description="Route priority (lower = higher)")


class AIProviderUpdate(BaseModel):
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    protocol: Optional[str] = None
    base_url: Optional[str] = None
    full_url_mode: Optional[bool] = None
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = Field(None, description="Set new API key (leave null to keep existing)")
    auth_header: Optional[str] = None
    auth_prefix: Optional[str] = None
    custom_headers: Optional[dict] = None
    proxy_config: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    tls_verify: Optional[bool] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AIProviderResponse(BaseModel):
    id: str
    provider_code: str
    provider_name: str
    provider_type: str
    protocol: str
    base_url: Optional[str] = None
    full_url_mode: bool = False
    endpoint_url: Optional[str] = None
    api_key_display: Optional[str] = Field(None, description="Masked API key (last 4 chars)")
    has_api_key: bool = False
    auth_header: str = "Authorization"
    auth_prefix: Optional[str] = "Bearer"
    custom_headers_json: dict = {}
    proxy_config_json: dict = {}
    timeout_seconds: int = 60
    retry_count: int = 2
    tls_verify: bool = True
    enabled: bool = False
    priority: int = 100
    health_status: str = "unknown"
    health_score: Optional[float] = None
    last_health_check_at: Optional[datetime] = None
    model_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AIProviderListResponse(BaseModel):
    items: list[AIProviderResponse]
    total: int
    page: int
    page_size: int
