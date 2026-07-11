from pydantic import BaseModel
from datetime import datetime


class ProductCategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0


class ProductCategoryResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    sort_order: int = 0

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    category_id: str | None = None
    name: str
    unit: str = "项"
    pricing_method: str = "quantity"
    default_price: float = 0
    min_charge: float = 0
    remark: str | None = None
    is_active: bool = True
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    area: float | None = None
    quantity: float | None = None


class ProductUpdate(BaseModel):
    category_id: str | None = None
    name: str | None = None
    unit: str | None = None
    pricing_method: str | None = None
    default_price: float | None = None
    min_charge: float | None = None
    remark: str | None = None
    is_active: bool | None = None
    material_id: str | None = None
    process_id: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    area: float | None = None
    quantity: float | None = None


class ProductResponse(BaseModel):
    id: str
    category_id: str | None = None
    name: str
    unit: str
    pricing_method: str
    default_price: float
    min_charge: float
    remark: str | None = None
    is_active: bool
    created_at: datetime | None = None
    material_id: str | None = None
    process_id: str | None = None
    material_name: str | None = None
    process_name: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    area: float | None = None
    quantity: float | None = None

    model_config = {"from_attributes": True}


class MaterialCreate(BaseModel):
    name: str
    spec: str | None = None
    unit: str = "张"
    purchase_price: float = 0
    sale_price: float = 0
    loss_rate: float = 0
    safe_stock: float = 0
    remark: str | None = None
    is_active: bool = True


class MaterialUpdate(BaseModel):
    name: str | None = None
    spec: str | None = None
    unit: str | None = None
    purchase_price: float | None = None
    sale_price: float | None = None
    loss_rate: float | None = None
    safe_stock: float | None = None
    remark: str | None = None
    is_active: bool | None = None


class MaterialResponse(BaseModel):
    id: str
    name: str
    spec: str | None = None
    unit: str
    purchase_price: float
    sale_price: float
    loss_rate: float
    safe_stock: float
    remark: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProcessCreate(BaseModel):
    name: str
    charge_method: str = "fixed"
    default_price: float = 0
    remark: str | None = None
    is_active: bool = True


class ProcessUpdate(BaseModel):
    name: str | None = None
    charge_method: str | None = None
    default_price: float | None = None
    remark: str | None = None
    is_active: bool | None = None


class ProcessResponse(BaseModel):
    id: str
    name: str
    charge_method: str
    default_price: float
    remark: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    name: str
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    supply_type: str | None = None
    bank_account: str | None = None
    remark: str | None = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    supply_type: str | None = None
    bank_account: str | None = None
    remark: str | None = None
    is_active: bool | None = None


class SupplierResponse(BaseModel):
    id: str
    supplier_no: str
    name: str
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    supply_type: str | None = None
    bank_account: str | None = None
    remark: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
