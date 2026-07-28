"""Pydantic schemas for Prompt Center - templates, versions, execution."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VariableDef(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Variable name (used in template)")
    label: str = Field("", max_length=200, description="Display label for UI")
    default: str = Field("", description="Default value")
    required: bool = Field(False, description="Whether variable is required")


# ── Template Schemas ──

class PromptTemplateCreate(BaseModel):
    template_code: str = Field(..., min_length=2, max_length=100, description="Unique code for the template")
    template_name: str = Field(..., min_length=1, max_length=200, description="Template display name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field("general", description="Category: general / system / business / custom")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    variables: list[VariableDef] = Field(default_factory=list, description="Template variable definitions")


class PromptTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    variables: Optional[list[VariableDef]] = None
    enabled: Optional[bool] = None


class PromptTemplateResponse(BaseModel):
    id: str
    template_code: str
    template_name: str
    description: Optional[str] = None
    category: str = "general"
    tags: list = []
    variables_json: list = []
    active_version_id: Optional[str] = None
    active_version_number: Optional[int] = None
    enabled: bool = True
    version: int = 1
    version_count: int = 0
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Version Schemas ──

class PromptVersionCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Prompt content with {{variable}} placeholders")
    variables_defaults: dict[str, str] = Field(default_factory=dict, description="Default values for variables")
    change_log: Optional[str] = Field(None, description="What changed in this version")
    activate: bool = Field(False, description="Activate this version immediately")


class PromptVersionUpdate(BaseModel):
    content: Optional[str] = None
    variables_defaults: Optional[dict[str, str]] = None
    change_log: Optional[str] = None
    status: Optional[str] = None


class PromptVersionResponse(BaseModel):
    id: str
    template_id: str
    version_number: int
    content: str
    variables_defaults_json: dict = {}
    change_log: Optional[str] = None
    status: str = "draft"
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Test Execution Schemas ──

class PromptTestRequest(BaseModel):
    version_id: Optional[str] = Field(None, description="Specific version to test (omit for active)")
    variables: dict[str, str] = Field(default_factory=dict, description="Variable values for substitution")
    messages: list[dict] = Field(default_factory=list, description="Additional chat messages after system prompt")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=1, le=131072)


class PromptTestResponse(BaseModel):
    output_text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    model_code: Optional[str] = None
    resolved_content: str
    log_id: str


# ── Execution Log Schemas ──

class ExecutionLogResponse(BaseModel):
    id: str
    template_id: Optional[str] = None
    template_code: Optional[str] = None
    template_name: Optional[str] = None
    version_id: Optional[str] = None
    version_number: Optional[int] = None
    resolved_content: str
    variables_used_json: dict = {}
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    model_code: Optional[str] = None
    output_text: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExecutionLogListResponse(BaseModel):
    items: list[ExecutionLogResponse]
    total: int
    page: int
    page_size: int
