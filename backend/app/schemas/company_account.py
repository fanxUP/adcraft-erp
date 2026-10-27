from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_type: Literal["bank", "wechat", "alipay", "cash", "other"]
    holder_name: str | None = Field(default=None, max_length=200)
    bank_name: str | None = Field(default=None, max_length=200)
    account_number: str | None = Field(default=None, max_length=200)
    is_active: bool = True
    is_default: bool = False
    remark: str | None = Field(default=None, max_length=2000)


class CompanyAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    account_type: Literal["bank", "wechat", "alipay", "cash", "other"] | None = None
    holder_name: str | None = Field(default=None, max_length=200)
    bank_name: str | None = Field(default=None, max_length=200)
    account_number: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    is_default: bool | None = None
    remark: str | None = Field(default=None, max_length=2000)


class PaymentAccountAssignment(BaseModel):
    payment_account_id: UUID
