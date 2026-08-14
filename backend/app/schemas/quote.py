from pydantic import BaseModel, Field, model_validator
from datetime import datetime, date


class QuoteItemCreate(BaseModel):
    id: str | None = None
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str = Field(..., min_length=1)
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
    material_process: str | None = None


class QuoteItemUpdate(BaseModel):
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str | None = Field(None, min_length=1)
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
    material_process: str | None = None


class QuoteItemResponse(BaseModel):
    id: str
    quote_id: str
    product_id: str | None = None
    material_id: str | None = None
    process_id: str | None = None
    item_name: str = Field(..., min_length=1)
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
    pieces: float | None = None
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
    project_name: str = Field(..., min_length=1)
    sales_user_id: str | None = None
    discount_amount: float = Field(0, ge=0)
    tax_rate: float = Field(0, ge=0, le=100)
    valid_until: date | None = None
    quote_date: date | None = None
    remark: str | None = None
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    items: list[QuoteItemCreate] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_customer(self):
        if not self.customer_id and not self.customer_name:
            raise ValueError("请选择已有客户或输入新客户名称")
        return self


class QuoteUpdate(BaseModel):
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    sales_user_id: str | None = None
    discount_amount: float | None = Field(None, ge=0)
    tax_rate: float | None = Field(None, ge=0, le=100)
    valid_until: date | None = None
    quote_date: date | None = None
    remark: str | None = None
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
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
    quote_date: str | None = None
    created_at: datetime | None = None
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None

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
    quote_date: str | None = None
    remark: str | None = None
    department: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    created_at: datetime | None = None
    items: list[QuoteItemResponse] = []

    model_config = {"from_attributes": True}
