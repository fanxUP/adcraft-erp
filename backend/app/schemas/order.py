from pydantic import BaseModel
from datetime import datetime


class OrderListResponse(BaseModel):
    id: str
    order_no: str
    customer_id: str
    project_name: str
    status: str
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrderItemResponse(BaseModel):
    id: str
    item_name: str
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float
    unit: str | None = None
    unit_price: float
    subtotal_amount: float
    remark: str | None = None

    model_config = {"from_attributes": True}


class OrderStatusLogResponse(BaseModel):
    id: str
    from_status: str | None = None
    to_status: str
    reason: str | None = None
    operated_by: str | None = None
    operated_at: str

    model_config = {"from_attributes": True}


class OrderDetailResponse(BaseModel):
    id: str
    order_no: str
    quote_id: str | None = None
    customer_id: str
    project_name: str
    sales_user_id: str | None = None
    status: str
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    delivery_deadline: str | None = None
    installation_address: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    items: list[OrderItemResponse] = []
    status_logs: list[OrderStatusLogResponse] = []

    model_config = {"from_attributes": True}


class OrderStatusChange(BaseModel):
    to_status: str
    reason: str | None = None
