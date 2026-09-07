from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field
from app.schemas.common import CoercedModel

from app.schemas.attachment import AttachmentResponse
from app.schemas.task_dependency import TaskDependencyTaskSummary


# -- Design Task --

class DesignTaskCreate(BaseModel):
    order_id: str
    customer_id: str | None = None
    project_name: str | None = None
    assigned_to: str | None = None
    description: str | None = None
    progress_pct: int = Field(0, ge=0, le=100)


class DesignTaskUpdate(BaseModel):
    project_name: str | None = None
    assigned_to: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)


class DesignTaskResponse(CoercedModel):
    model_config = {"from_attributes": True}
    id: str
    design_no: str
    document_id: str
    order_id: str | None = None
    customer_id: str
    project_name: str
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocking_tasks: list[TaskDependencyTaskSummary] = Field(default_factory=list)
    assigned_to: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    department: str | None = None
    total_amount: float | None = None
    source: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    department: str | None = None
    total_amount: float | None = None
    source: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = Field(default_factory=list)


# -- Production Task --

class ProductionTaskCreate(BaseModel):
    order_id: str
    customer_id: str | None = None
    project_name: str | None = None
    assigned_to: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float = 1
    progress_pct: int = Field(0, ge=0, le=100)


class ProductionTaskUpdate(BaseModel):
    project_name: str | None = None
    assigned_to: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float | None = None
    qc_result: str | None = None
    rework_reason: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)


class ProductionTaskResponse(CoercedModel):
    model_config = {"from_attributes": True}
    id: str
    production_no: str
    document_id: str
    order_id: str | None = None
    customer_id: str
    project_name: str
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocking_tasks: list[TaskDependencyTaskSummary] = Field(default_factory=list)
    assigned_to: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float = 1
    qc_result: str | None = None
    rework_reason: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    department: str | None = None
    total_amount: float | None = None
    source: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = Field(default_factory=list)


# -- Installation Task --

class InstallationTaskCreate(BaseModel):
    order_id: str
    customer_id: str | None = None
    project_name: str | None = None
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    progress_pct: int = Field(0, ge=0, le=100)


class InstallationTaskUpdate(BaseModel):
    project_name: str | None = None
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    acceptance_result: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)


class InstallationTaskResponse(CoercedModel):
    model_config = {"from_attributes": True}
    id: str
    installation_no: str
    document_id: str
    order_id: str | None = None
    customer_id: str
    project_name: str
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocking_tasks: list[TaskDependencyTaskSummary] = Field(default_factory=list)
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    acceptance_result: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = Field(default_factory=list)


# -- Status change --

class TaskStatusChange(BaseModel):
    to_status: str
    reason: str | None = None


class TaskQueueItem(CoercedModel):
    """统一项目队列中的任务卡片数据。"""

    model_config = {"from_attributes": True}

    id: str
    task_type: Literal["design", "production", "installation"]
    stage: Literal["design", "production", "installation"]
    task_no: str
    document_id: str
    order_id: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    project_name: str
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocking_tasks: list[TaskDependencyTaskSummary] = Field(default_factory=list)
    assigned_to: str | None = None
    assigned_to_name: str | None = None
    is_outsourced: bool = False
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
