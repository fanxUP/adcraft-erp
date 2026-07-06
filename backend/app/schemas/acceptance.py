from pydantic import BaseModel
from typing import Optional


class AcceptanceItemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    acceptance_id: str
    order_item_id: Optional[str] = None
    item_name: str
    material_process: Optional[str] = None
    specification: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    area: Optional[float] = None
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None
    image_url: Optional[str] = None
    item_status: str
    remark: Optional[str] = None
    group_name: Optional[str] = None


class AcceptanceAttachmentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    acceptance_id: str
    filename: str
    filepath: str
    filesize: Optional[int] = None
    upload_by: Optional[str] = None


class AcceptanceListResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    acceptance_no: str
    order_id: str
    order_no: Optional[str] = None
    customer_name: Optional[str] = None
    status: str
    accepted_at: Optional[str] = None
    accepted_by: Optional[str] = None
    department: str | None = None
    created_at: str


class AcceptanceDetailResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    acceptance_no: str
    order_id: str
    order_no: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    contact_person: Optional[str] = None
    order_date: Optional[str] = None
    project_name: Optional[str] = None
    department: Optional[str] = None
    status: str
    accepted_at: Optional[str] = None
    accepted_by: Optional[str] = None
    our_acceptor_id: Optional[str] = None
    our_acceptor_name: Optional[str] = None
    remark: Optional[str] = None
    reject_reason: Optional[str] = None
    discount_amount: float = 0
    advance_amount: float = 0
    created_at: str
    updated_at: str
    items: list[AcceptanceItemResponse] = []
    attachments: list[AcceptanceAttachmentResponse] = []


class AcceptanceStatusChange(BaseModel):
    to_status: str
    reason: Optional[str] = None
