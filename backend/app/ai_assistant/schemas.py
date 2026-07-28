"""AI Assistant Pydantic schemas."""

from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ──


class AiPageContext(BaseModel):
    page: Optional[str] = Field(default=None, max_length=128)
    page_title: Optional[str] = Field(default=None, max_length=80)
    page_purpose: Optional[str] = Field(default=None, max_length=300)
    workflow_stage: Optional[str] = Field(default=None, max_length=64)
    available_actions: list[str] = Field(default_factory=list, max_length=12)
    business_type: Optional[str] = Field(default=None, max_length=64)
    business_id: Optional[str] = Field(default=None, max_length=64)
    business_status: Optional[str] = Field(default=None, max_length=64)
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_no: Optional[str] = None
    order_id: Optional[str] = None
    order_no: Optional[str] = None
    quote_id: Optional[str] = None
    quote_no: Optional[str] = None
    project_name: Optional[str] = None
    task_id: Optional[str] = None
    task_type: Optional[str] = None


class AiChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    context: Optional[AiPageContext] = None


class AiConfirmActionRequest(BaseModel):
    pass


class AiCancelActionRequest(BaseModel):
    reason: Optional[str] = None


# ── Response schemas ──


class AiToolCallResult(BaseModel):
    tool_name: str
    status: str  # success/failed/blocked/waiting_confirmation
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class AiPendingActionResponse(BaseModel):
    id: str
    action_type: str
    tool_name: str
    preview_data: dict[str, Any]
    status: str
    expires_at: Optional[str] = None


class AiChatResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    tool_calls: list[AiToolCallResult] = []
    pending_action: Optional[AiPendingActionResponse] = None


# ── Session / Message list schemas ──


class AiSessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    current_page: Optional[str] = None
    current_business_type: Optional[str] = None
    current_business_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AiMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: Optional[str] = None


# ── Tool definition schema (for prompt construction) ──


class ToolParamProperty(BaseModel):
    type: str = "string"
    description: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    risk_level: str  # level_1/level_2/level_3/level_4
    required_permission: str
    requires_confirmation: bool = False
