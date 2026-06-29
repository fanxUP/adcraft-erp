from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.attachment import AttachmentResponse


# -- Design Task --

class DesignTaskCreate(BaseModel):
    order_id: str
    customer_id: str
    project_name: str
    assigned_to: str | None = None
    description: str | None = None


class DesignTaskUpdate(BaseModel):
    project_name: str | None = None
    assigned_to: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None


class DesignTaskResponse(BaseModel):
    id: str
    design_no: str
    order_id: str
    customer_id: str
    project_name: str
    status: str
    assigned_to: str | None = None
    description: str | None = None
    design_file_url: str | None = None
    client_comments: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = []


# -- Production Task --

class ProductionTaskCreate(BaseModel):
    order_id: str
    customer_id: str
    project_name: str
    assigned_to: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float = 1


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


class ProductionTaskResponse(BaseModel):
    id: str
    production_no: str
    order_id: str
    customer_id: str
    project_name: str
    status: str
    assigned_to: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float = 1
    qc_result: str | None = None
    rework_reason: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = []


# -- Installation Task --

class InstallationTaskCreate(BaseModel):
    order_id: str
    customer_id: str
    project_name: str
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None


class InstallationTaskUpdate(BaseModel):
    project_name: str | None = None
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    acceptance_result: str | None = None


class InstallationTaskResponse(BaseModel):
    id: str
    installation_no: str
    order_id: str
    customer_id: str
    project_name: str
    status: str
    assigned_to: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    scheduled_at: str | None = None
    acceptance_result: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachments: list[AttachmentResponse] = []


# -- Status change --

class TaskStatusChange(BaseModel):
    to_status: str
    reason: str | None = None
