from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.attachment import AttachmentResponse
from app.schemas.common import ActionCapability, CoercedModel, StatusView
from app.schemas.order import OrderItemResponse

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
    status_view: StatusView | None = None
    capabilities: dict[str, ActionCapability] = Field(default_factory=dict)
    assignee_user_id: str | None = None
    assignee_name: str | None = None
    assignee_state: Literal["unassigned", "claimed", "historical_unknown", "terminal"] = "unassigned"


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
    assigned_to_name: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    department: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
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
    assigned_to_name: str | None = None
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
    contact_name: str | None = None
    contact_phone: str | None = None
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
    assigned_to_name: str | None = None
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

class TaskAssigneeUpdate(BaseModel):
    """Change only the task owner through the dedicated assignment endpoint."""

    assigned_to: str | None = None


class TaskItemAssigneeUpdate(BaseModel):
    """Assign or release the explicitly selected order-item work units."""

    order_item_ids: list[str] = Field(min_length=1, max_length=100)
    assignee_user_id: str | None = None


class TaskStatusChange(BaseModel):
    to_status: str
    reason: str | None = None
    order_item_ids: list[str] = Field(min_length=1, max_length=100)
    assigned_to: str | None = None


class TaskItemAction(BaseModel):
    """One server-authorized action for a single order-item work unit."""

    key: str
    to_status: str
    label: str
    allowed: bool
    disabled_reason: str | None = None
    kind: Literal["primary", "secondary"] = "secondary"
    requires_confirmation: bool = True


class TaskOrderItemOption(OrderItemResponse):
    """任务处理页使用的订单明细阶段与可选性。"""

    # Price fields are optional because the operational task response omits
    # them entirely for users without order-item price permission.  Sales,
    # finance and admin viewers still receive the original values.
    unit_price: float | None = None
    process_fee: float | None = None
    installation_fee: float | None = None
    design_fee: float | None = None
    transport_fee: float | None = None
    other_fee: float | None = None
    subtotal_amount: float | None = None

    stage: Literal[
        "designing",
        "in_production",
        "in_installation",
        "completed",
        "not_ready",
    ]
    stage_label: str
    stage_view: StatusView
    can_select: bool = False
    disabled_reason: str | None = None
    is_linked: bool = False
    task_status: str | None = None
    assignee_user_id: str | None = None
    assignee_name: str | None = None
    assignee_state: Literal["unassigned", "claimed", "historical_unknown", "terminal"] = "unassigned"
    task_status_label: str | None = None
    task_status_view: StatusView | None = None
    task_progress_pct: int | None = Field(default=None, ge=0, le=100)
    capabilities: dict[str, ActionCapability] = Field(default_factory=dict)
    actions: list[TaskItemAction] = Field(default_factory=list)
    outsource_blocked: bool = False
    outsource_status: Literal["pending", "in_progress"] | None = None
    outsource_status_label: str | None = None
    outsource_task_count: int = Field(default=0, ge=0)
    outsource_task_nos: list[str] = Field(default_factory=list)


class TaskAssigneeOption(BaseModel):
    """Active employee option with the user id stored on task rows."""

    id: str
    name: str
    employee_no: str
    user_id: str


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
    department: str | None = None
    project_name: str
    item_name: str | None = None
    item_names: list[str] = Field(default_factory=list)
    status: str
    progress_pct: int = Field(0, ge=0, le=100)
    total_amount: float | None = None
    status_view: StatusView | None = None
    capabilities: dict[str, ActionCapability] = Field(default_factory=dict)
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


class CompletedProjectCard(CoercedModel):
    """Read-only project card for the completed column."""

    model_config = {"from_attributes": True}

    kind: Literal["project"] = "project"
    project_id: str
    project_no: str
    project_name: str
    customer_name: str | None = None
    department: str | None = None
    status: Literal["completed"] = "completed"
    completed_at: str | None = None
    completed_detail_count: int = Field(0, ge=0)
    completed_work_unit_count: int = Field(0, ge=0)
    stages: list[TaskType] = Field(default_factory=list)
    scope: Literal["all", "own"]
    total_amount: float | None = None


class CompletedProjectStage(CoercedModel):
    """One authorized completion snapshot for a stage and order item."""

    status: Literal["completed"] = "completed"
    status_label: str = "已完成"
    employee_id: str | None = None
    employee_name: str = "未分配"
    completed_at: str | None = None
    task_id: str
    task_no: str | None = None
    source: str = "live"


class CompletedProjectDetailItem(CoercedModel):
    """One active order item with independent design/production/installation cells."""

    kind: Literal["detail"] = "detail"
    project_id: str
    project_no: str
    project_name: str
    order_item_id: str
    item_name: str
    material_process: str | None = None
    specification: str | None = None
    quantity: float | None = None
    unit: str | None = None
    stages: dict[TaskType, CompletedProjectStage | None] = Field(default_factory=dict)


class CompletedProjectResourceTask(CoercedModel):
    """One visible task and its read-only attachment list."""

    task_id: str
    task_no: str | None = None
    attachments: list[AttachmentResponse] = Field(default_factory=list)


class CompletedProjectResourceSection(CoercedModel):
    """Resources grouped by one delivery stage."""

    task_type: TaskType
    task_label: str
    task_count: int = Field(0, ge=0)
    attachment_count: int = Field(0, ge=0)
    tasks: list[CompletedProjectResourceTask] = Field(default_factory=list)


class CompletedProjectDetail(CompletedProjectCard):
    """Read-only completed project detail page payload."""

    items: list[CompletedProjectDetailItem] = Field(default_factory=list)
    resources: dict[TaskType, CompletedProjectResourceSection] = Field(default_factory=dict)
