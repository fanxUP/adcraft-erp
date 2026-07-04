from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class CustomerCreate(BaseModel):
    name: str
    customer_type: str | None = None
    level: str | None = None
    phone: str | None = None
    wechat: str | None = None
    address: str | None = None
    tax_no: str | None = None
    invoice_info: str | None = None
    default_payment_days: int = 0
    default_discount: float = 1.0
    remark: str | None = None
    contacts: list["ContactCreate"] = []


class ContactCreate(BaseModel):
    name: str
    phone: str | None = None
    wechat: str | None = None
    position: str | None = None
    is_primary: bool = False
    remark: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    customer_type: str | None = None
    level: str | None = None
    phone: str | None = None
    wechat: str | None = None
    address: str | None = None
    tax_no: str | None = None
    invoice_info: str | None = None
    default_payment_days: int | None = None
    default_discount: float | None = None
    remark: str | None = None
    contacts: list[ContactCreate] | None = None


class ContactResponse(BaseModel):
    id: str
    name: str
    phone: str | None = None
    wechat: str | None = None
    position: str | None = None
    is_primary: bool = False
    remark: str | None = None

    model_config = {"from_attributes": True}


class CustomerResponse(BaseModel):
    id: str
    customer_no: str
    name: str
    customer_type: str | None = None
    level: str | None = None
    phone: str | None = None
    wechat: str | None = None
    address: str | None = None
    tax_no: str | None = None
    invoice_info: str | None = None
    default_payment_days: int = 0
    default_discount: float = 1.0
    remark: str | None = None
    created_at: datetime | None = None
    contacts: list[ContactResponse] = []

    model_config = {"from_attributes": True}
