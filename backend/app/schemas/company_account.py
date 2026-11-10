from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


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


class OpeningBalanceSet(BaseModel):
    entry_date: date
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class BankLedgerEntryCreate(BaseModel):
    request_id: UUID
    entry_date: date
    direction: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    summary: str = Field(default="", max_length=255)
    counterparty_account: str | None = Field(default=None, max_length=200)
    counterparty_name: str | None = Field(default=None, max_length=255)
    counterparty_supplier_id: UUID | None = None
    category: str | None = Field(default=None, max_length=64)
    project_name: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    order_id: UUID | None = None


class BankProjectCostCreate(BaseModel):
    request_id: UUID
    entry_date: date
    order_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    category: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    summary: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    supplier_id: UUID | None = None
    counterparty_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class BankCustomerReceiptCreate(BaseModel):
    request_id: UUID
    entry_date: date
    order_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    summary: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
