from typing import Any, Literal

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
    design_progress_pct: int = Field(0, ge=0, le=100)
    production_progress_pct: int = Field(0, ge=0, le=100)
    installation_progress_pct: int = Field(0, ge=0, le=100)
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
    lifecycle_status: str = "active"

    model_config = {"from_attributes": True}


class OrderStatusLogResponse(BaseModel):
    id: str
    from_status: str | None = None
    to_status: str
    reason: str | None = None
    operated_by: str | None = None
    operated_at: str

    model_config = {"from_attributes": True}


class OrderGroupResponse(BaseModel):
    id: str
    quote_id: str
    group_id: str
    group_name: str | None = None
    sort_order: int = 0


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
    updated_at: datetime | None = None
    items: list[OrderItemResponse] = []
    groups: list[OrderGroupResponse] = []
    status_logs: list[OrderStatusLogResponse] = []

    model_config = {"from_attributes": True}


class OrderStatusChange(BaseModel):
    to_status: str
    reason: str | None = None


class OrderItemMutationBase(BaseModel):
    """审计和并发控制字段，订单明细接口必须携带。"""

    reason: str = Field(..., min_length=1, max_length=500)
    expected_updated_at: str = Field(..., min_length=1)
    preview_id: str | None = None
    plan_hash: str | None = None
    preview_expires_at: str | None = None
    confirm_high_risk: bool = False


class OrderItemCreate(OrderItemMutationBase):
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str = Field(..., min_length=1, max_length=255)
    length: float | None = Field(None, ge=0)
    length_unit: str | None = "m"
    width: float | None = Field(None, ge=0)
    width_unit: str | None = "m"
    height: float | None = Field(None, ge=0)
    height_unit: str | None = "m"
    quantity: float = Field(1, gt=0)
    unit: str | None = None
    use_area: bool = False
    quantity_mode: str = "piece"
    pieces: float | None = Field(1, gt=0)
    unit_price: float = Field(0, ge=0)
    process_fee: float = Field(0, ge=0)
    installation_fee: float = Field(0, ge=0)
    design_fee: float = Field(0, ge=0)
    transport_fee: float = Field(0, ge=0)
    other_fee: float = Field(0, ge=0)
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    group_id: str | None = None
    material_process: str | None = None


class OrderItemUpdate(OrderItemMutationBase):
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str | None = Field(None, min_length=1, max_length=255)
    length: float | None = Field(None, ge=0)
    length_unit: str | None = None
    width: float | None = Field(None, ge=0)
    width_unit: str | None = None
    height: float | None = Field(None, ge=0)
    height_unit: str | None = None
    quantity: float | None = Field(None, gt=0)
    unit: str | None = None
    use_area: bool | None = None
    quantity_mode: str | None = None
    pieces: float | None = Field(None, gt=0)
    unit_price: float | None = Field(None, ge=0)
    process_fee: float | None = Field(None, ge=0)
    installation_fee: float | None = Field(None, ge=0)
    design_fee: float | None = Field(None, ge=0)
    transport_fee: float | None = Field(None, ge=0)
    other_fee: float | None = Field(None, ge=0)
    remark: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    group_name: str | None = None
    group_id: str | None = None
    material_process: str | None = None


class OrderItemDelete(OrderItemMutationBase):
    pass


class OrderItemMutationPreview(OrderItemMutationBase):
    operation: Literal["add", "update", "delete"]
    item_id: str | None = None
    item: dict[str, Any] | None = None


class OrderEditHeader(BaseModel):
    """报价式订单编辑页允许修改的订单头字段。

    订单编号、状态、来源报价、已收款和成本等事实字段不在此模型中，
    由后端根据当前订单保留，避免客户端把展示数据当成可写数据提交。
    """

    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str | None = Field(None, min_length=1, max_length=255)
    department: str | None = Field(None, max_length=255)
    contact_person: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=100)
    delivery_deadline: str | None = None
    installation_address: str | None = Field(None, max_length=500)
    remark: str | None = Field(None, max_length=2000)


class OrderEditItem(BaseModel):
    """订单编辑页提交的完整明细快照。

    subtotal_amount、area、specification、lifecycle_status 等派生/事实字段
    不接受前端提交，服务层统一重算或保留数据库事实。
    """

    id: str | None = None
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str = Field(..., min_length=1, max_length=255)
    length: float | None = Field(None, ge=0)
    length_unit: str | None = "m"
    width: float | None = Field(None, ge=0)
    width_unit: str | None = "m"
    height: float | None = Field(None, ge=0)
    height_unit: str | None = "m"
    quantity: float = Field(1, gt=0)
    unit: str | None = None
    use_area: bool = False
    quantity_mode: str = "piece"
    pieces: float | None = Field(1, gt=0)
    unit_price: float = Field(0, ge=0)
    process_fee: float = Field(0, ge=0)
    installation_fee: float = Field(0, ge=0)
    design_fee: float = Field(0, ge=0)
    transport_fee: float = Field(0, ge=0)
    other_fee: float = Field(0, ge=0)
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    group_id: str | None = None
    material_process: str | None = None


class OrderEditGroup(BaseModel):
    group_id: str = Field(..., min_length=1, max_length=100)
    group_name: str | None = Field(None, max_length=255)
    sort_order: int = 0


class OrderEditRequest(OrderItemMutationBase):
    """订单完整编辑的批量预检/应用请求。"""

    header: OrderEditHeader = Field(default_factory=OrderEditHeader)
    items: list[OrderEditItem] = Field(default_factory=list)
    groups: list[OrderEditGroup] = Field(default_factory=list)
