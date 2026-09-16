from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import CoercedModel


SUPPLIER_TYPES = {
    "outsource": "外协服务",
    "material": "材料供应商",
    "equipment": "设备供应商",
    "transport": "运输服务",
    "service": "其他服务",
    "other": "其他供应商",
}


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=128)
    supplier_type: str = "other"
    contact_person: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=128)
    address: str | None = None
    tax_id: str | None = Field(None, max_length=64)
    bank_name: str | None = Field(None, max_length=128)
    bank_account: str | None = Field(None, max_length=128)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    settlement_method: str | None = Field(None, max_length=32)
    settlement_days: int | None = Field(None, ge=0, le=3650)
    service_type: str | None = Field(None, max_length=64)
    coop_rating: str | None = Field(None, max_length=16)
    remark: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_required(cls, value):
        value = str(value or "").strip()
        if not value:
            raise ValueError("供应商名称不能为空")
        return value


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=128)
    supplier_type: str | None = None
    contact_person: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=128)
    address: str | None = None
    tax_id: str | None = Field(None, max_length=64)
    bank_name: str | None = Field(None, max_length=128)
    bank_account: str | None = Field(None, max_length=128)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    settlement_method: str | None = Field(None, max_length=32)
    settlement_days: int | None = Field(None, ge=0, le=3650)
    service_type: str | None = Field(None, max_length=64)
    coop_rating: str | None = Field(None, max_length=16)
    remark: str | None = None
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return str(value).strip() if value is not None else value


class SupplierStats(CoercedModel):
    project_cost_count: int = 0
    project_cost_amount: float = 0
    project_cost_payable: float = 0
    project_cost_paid: float = 0
    project_cost_remaining: float = 0
    expense_count: int = 0
    expense_amount: float = 0
    expense_payable: float = 0
    expense_paid: float = 0
    expense_remaining: float = 0
    outsource_task_count: int = 0
    outsource_task_amount: float = 0
    outsource_task_unpaid: float = 0


class SupplierResponse(CoercedModel):
    id: str
    vendor_no: str
    name: str
    short_name: str | None = None
    supplier_type: str = "other"
    supplier_type_label: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    tax_id: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    tax_rate: float | None = None
    settlement_method: str | None = None
    settlement_days: int | None = None
    service_type: str | None = None
    coop_rating: str | None = None
    remark: str | None = None
    is_active: bool = True
    created_at: str | None = None
    stats: SupplierStats | None = None
