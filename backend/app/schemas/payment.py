from pydantic import BaseModel, field_validator
from datetime import datetime
from uuid import UUID


class PaymentCreate(BaseModel):
    order_id: UUID
    customer_id: UUID
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    receipt_url: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("收款金额必须大于0")
        return v


class PaymentResponse(BaseModel):
    id: str
    payment_no: str
    order_id: str
    customer_id: str
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    is_voided: bool
    void_reason: str | None = None
    voided_at: str | None = None
    receipt_url: str | None = None
    created_at: str | None = None
    created_by: str | None = None

    model_config = {"from_attributes": True}


class PaymentVoid(BaseModel):
    void_reason: str


class StatementCreate(BaseModel):
    customer_id: UUID
    start_date: str
    end_date: str


class StatementResponse(BaseModel):
    id: str
    statement_no: str
    customer_id: str
    start_date: str | None = None
    end_date: str | None = None
    total_order_amount: float
    total_paid_amount: float
    total_unpaid_amount: float
    status: str
    confirmed_at: str | None = None
    confirmed_by: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class StatementDetailResponse(StatementResponse):
    orders: list["StatementOrderItem"] = []
    payments: list["StatementPaymentItem"] = []


class StatementOrderItem(BaseModel):
    id: str
    order_no: str
    project_name: str
    status: str
    total_amount: float
    paid_amount: float
    unpaid_amount: float


class StatementPaymentItem(BaseModel):
    id: str
    payment_no: str
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    is_voided: bool


class ExpenseCreate(BaseModel):
    category: str | None = None
    amount: float
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("支出金额必须大于0")
        return v


class ExpenseUpdate(BaseModel):
    category: str | None = None
    amount: float | None = None
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None


class ExpenseResponse(BaseModel):
    id: str
    expense_no: str
    category: str | None = None
    amount: float
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None
    created_by: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


# ── Project Cost ──

class ProjectCostCreate(BaseModel):
    order_id: str
    category: str
    amount: float
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    order_item_id: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("成本金额必须大于0")
        return v

    @field_validator("order_id")
    @classmethod
    def order_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("订单ID不能为空")
        return v.strip()


class ProjectCostUpdate(BaseModel):
    category: str | None = None
    amount: float | None = None
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    order_item_id: str | None = None


class ProjectCostResponse(BaseModel):
    id: str
    cost_no: str
    order_id: str
    order_item_id: str | None = None
    order_item_name: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    category: str
    amount: float
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    created_by: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}
