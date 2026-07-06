from pydantic import BaseModel, model_validator
from datetime import datetime, date


class QuoteItemCreate(BaseModel):
    id: str | None = None
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str
    length: float | None = None
    length_unit: str | None = "m"
    width: float | None = None
    width_unit: str | None = "m"
    height: float | None = None
    height_unit: str | None = "m"
    quantity: float = 1
    unit: str | None = None
    use_area: bool = False
    quantity_mode: str = "piece"
    unit_price: float = 0
    process_fee: float = 0
    installation_fee: float = 0
    design_fee: float = 0
    transport_fee: float = 0
    other_fee: float = 0
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    material_process: str | None = None


class QuoteItemUpdate(BaseModel):
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str | None = None
    length: float | None = None
    length_unit: str | None = None
    width: float | None = None
    width_unit: str | None = None
    height: float | None = None
    height_unit: str | None = None
    quantity: float | None = None
    unit: str | None = None
    use_area: bool | None = None
    quantity_mode: str | None = None
    unit_price: float | None = None
    process_fee: float | None = None
    installation_fee: float | None = None
    design_fee: float | None = None
    transport_fee: float | None = None
    other_fee: float | None = None
    remark: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    group_name: str | None = None
    material_process: str | None = None


class QuoteItemResponse(BaseModel):
    id: str
    quote_id: str
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str
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
    unit_price: float
    process_fee: float
    installation_fee: float
    design_fee: float
    transport_fee: float
    other_fee: float
    subtotal_amount: float
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    material_process: str | None = None

    model_config = {"from_attributes": True}


class QuoteCreate(BaseModel):
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str
    sales_user_id: str | None = None
    tax_rate: float = 0
    valid_until: date | None = None
    remark: str | None = None
    department: str | None = None
    items: list[QuoteItemCreate] = []

    @model_validator(mode='after')
    def check_customer(self):
        if not self.customer_id and not self.customer_name:
            raise ValueError("请选择已有客户或输入新客户名称")
        return self


class QuoteUpdate(BaseModel):
    project_name: str | None = None
    sales_user_id: str | None = None
    discount_amount: float | None = None
    tax_rate: float | None = None
    valid_until: date | None = None
    remark: str | None = None
    department: str | None = None
    items: list[QuoteItemCreate] | None = None


class QuoteListResponse(BaseModel):
    id: str
    quote_no: str
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str
    status: str
    total_amount: float
    valid_until: str | None = None
    created_at: datetime | None = None
    department: str | None = None

    model_config = {"from_attributes": True}


class QuoteDetailResponse(BaseModel):
    id: str
    quote_no: str
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str
    sales_user_id: str | None = None
    status: str
    subtotal_amount: float
    discount_amount: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    valid_until: str | None = None
    remark: str | None = None
    department: str | None = None
    created_at: datetime | None = None
    items: list[QuoteItemResponse] = []

    model_config = {"from_attributes": True}
