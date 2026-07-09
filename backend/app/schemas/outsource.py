from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Vendor ──

class VendorCreate(BaseModel):
    name: str = Field(..., max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    service_type: str | None = None
    coop_rating: str | None = None
    remark: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    service_type: str | None = None
    coop_rating: str | None = None
    remark: str | None = None
    is_active: bool | None = None


class VendorResponse(BaseModel):
    id: str
    vendor_no: str
    name: str
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    service_type: str | None = None
    coop_rating: str | None = None
    remark: str | None = None
    is_active: bool = True
    created_at: str | None = None


# ── Task ──

class OutsourceTaskCreate(BaseModel):
    vendor_id: str = Field(...)
    related_doc_id: str | None = None
    related_doc_type: str | None = None
    related_doc_no: str | None = None
    order_id: str | None = None
    task_type: str = Field(...)
    description: str | None = None
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    expected_at: str | None = None
    remark: str | None = None


class OutsourceTaskUpdate(BaseModel):
    vendor_id: str | None = None
    related_doc_id: str | None = None
    related_doc_type: str | None = None
    task_type: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    status: str | None = None
    expected_at: str | None = None
    completed_at: str | None = None
    remark: str | None = None


class OutsourceTaskResponse(BaseModel):
    id: str
    task_no: str
    vendor_id: str
    vendor_name: str | None = None
    related_doc_id: str | None = None
    related_doc_type: str | None = None
    related_doc_no: str | None = None
    order_id: str | None = None
    task_type: str
    description: str | None = None
    quantity: int = 1
    unit_price: float = 0
    total_amount: float = 0
    status: str = "pending"
    expected_at: str | None = None
    completed_at: str | None = None
    remark: str | None = None
    created_at: str | None = None


# ── Payment ──

class OutsourcePaymentCreate(BaseModel):
    vendor_id: str = Field(...)
    task_id: str | None = None
    amount: Decimal = Field(...)
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None


class OutsourcePaymentResponse(BaseModel):
    id: str
    payment_no: str
    vendor_id: str
    vendor_name: str | None = None
    task_id: str | None = None
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    created_by: str | None = None
    created_at: str | None = None
