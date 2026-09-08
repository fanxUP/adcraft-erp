from datetime import datetime, timezone
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field, model_validator
from app.schemas.common import CoercedModel
from app.schemas.order import OrderItemResponse

from app.schemas.attachment import AttachmentResponse


TaskType = Literal["design", "production", "installation"]


def _comparable_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class TaskScheduleInput(BaseModel):
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule_range(self):
        if self.planned_start_at and self.planned_end_at:
            if _comparable_datetime(self.planned_end_at) < _comparable_datetime(self.planned_start_at):
                raise ValueError("计划结束时间不能早于计划开始时间")
        return self


class TaskOrderItemState(BaseModel):
    """状态快照 for one order item inside a multi-item task."""

    status: str
    status_label: str | None = None
    progress_pct: int = Field(0, ge=0, le=100)


# -- Design Task --

class DesignTaskCreate(TaskScheduleInput):
    order_id: str
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
    customer_id: str | None = None
    project_name: str | None = None
    assigned_to: str | None = None
    description: str | None = None
    progress_pct: int = Field(0, ge=0, le=100)


class DesignTaskUpdate(TaskScheduleInput):
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
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
    order_item_id: str | None = None
    order_item_ids: list[str] = Field(default_factory=list)
    order_item_states: dict[str, TaskOrderItemState] = Field(default_factory=dict)
    customer_id: str
    project_name: str
    item_name: str | None = None
    item_names: list[str] = Field(default_factory=list)
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    is_overdue: bool = False
    overdue_days: int = 0
    assigned_to: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None
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

class ProductionTaskCreate(TaskScheduleInput):
    order_id: str
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
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


class ProductionTaskUpdate(TaskScheduleInput):
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
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
    order_item_id: str | None = None
    order_item_ids: list[str] = Field(default_factory=list)
    order_item_states: dict[str, TaskOrderItemState] = Field(default_factory=dict)
    customer_id: str
    project_name: str
    item_name: str | None = None
    item_names: list[str] = Field(default_factory=list)
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    is_overdue: bool = False
    overdue_days: int = 0
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

class InstallationTaskCreate(TaskScheduleInput):
    order_id: str
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
    customer_id: str | None = None
    project_name: str | None = None
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    progress_pct: int = Field(0, ge=0, le=100)


class InstallationTaskUpdate(TaskScheduleInput):
    order_item_id: str | None = None
    order_item_ids: list[str] | None = Field(default=None, max_length=100)
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
    order_item_id: str | None = None
    order_item_ids: list[str] = Field(default_factory=list)
    order_item_states: dict[str, TaskOrderItemState] = Field(default_factory=dict)
    customer_id: str
    project_name: str
    item_name: str | None = None
    item_names: list[str] = Field(default_factory=list)
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    is_overdue: bool = False
    overdue_days: int = 0
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
    order_item_ids: list[str] = Field(min_length=1, max_length=100)


class TaskHistoryItem(CoercedModel):
    id: str
    task_type: Literal["design", "production", "installation"]
    task_id: str
    action: Literal["create", "update", "status_change"]
    user_id: str | None = None
    user_name: str | None = None
    changed_at: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    from_progress_pct: int | None = None
    to_progress_pct: int | None = None
    reason: str | None = None
    changed_fields: list[str] = Field(default_factory=list)


class TaskOrderItemOption(OrderItemResponse):
    """任务处理页使用的订单明细阶段与可选性。"""

    stage: Literal[
        "designing",
        "in_production",
        "in_installation",
        "completed",
        "not_ready",
    ]
    stage_label: str
    can_select: bool = False
    disabled_reason: str | None = None
    is_linked: bool = False
    task_status: str | None = None
    task_status_label: str | None = None
    task_progress_pct: int | None = Field(default=None, ge=0, le=100)
    outsource_blocked: bool = False
    outsource_status: Literal["pending", "in_progress"] | None = None
    outsource_status_label: str | None = None
    outsource_task_count: int = Field(default=0, ge=0)
    outsource_task_nos: list[str] = Field(default_factory=list)


class TaskQueueItem(CoercedModel):
    """统一项目队列中的任务卡片数据。"""

    model_config = {"from_attributes": True}

    id: str
    task_type: Literal["design", "production", "installation"]
    stage: Literal["design", "production", "installation"]
    task_no: str
    document_id: str
    order_id: str | None = None
    order_item_id: str | None = None
    order_item_ids: list[str] = Field(default_factory=list)
    order_no: str | None = None
    customer_name: str | None = None
    project_name: str
    item_name: str | None = None
    item_names: list[str] = Field(default_factory=list)
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    is_overdue: bool = False
    overdue_days: int = 0
    assigned_to: str | None = None
    assigned_to_name: str | None = None
    is_outsourced: bool = False
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
