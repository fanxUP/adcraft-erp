from pydantic import BaseModel, Field
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
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrderItemResponse(BaseModel):
    id: str
    item_name: str = Field(..., min_length=1)
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    length_unit: str | None = "m"
    width: float | None = None
    width_unit: str | None = "m"
    height: float | None = None
    height_unit: str | None = "m"
    quantity: float
    unit: str | None = None
    use_area: bool = False
    quantity_mode: str = "piece"
    area: float | None = None
    pieces: float | None = None
    unit_price: float
    process_fee: float = 0
    installation_fee: float = 0
    design_fee: float = 0
    transport_fee: float = 0
    other_fee: float = 0
    subtotal_amount: float
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    material_process: str | None = None

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
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    created_at: datetime | None = None
    items: list[OrderItemResponse] = []
    status_logs: list[OrderStatusLogResponse] = []

    model_config = {"from_attributes": True}


class OrderStatusChange(BaseModel):
    to_status: str
    reason: str | None = None
