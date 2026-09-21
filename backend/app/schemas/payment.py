from app.schemas.common import ActionCapability, CoercedModel, StatusView
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class PaymentCreate(BaseModel):
    # New writes are contract-scoped. order_id remains optional for old
    # clients; the service resolves it to the unique active contract.
    contract_id: UUID | None = None
    order_id: UUID | None = None
    customer_id: UUID
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    receipt_url: str | None = None

    @field_validator("contract_id", "order_id", mode="before")
    @classmethod
    def empty_ids_to_none(cls, value):
        return value or None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("收款金额必须大于0")
        return v


class PaymentAllocationResponse(CoercedModel):
    id: str
    contract_id: str
    document_id: str | None = None
    order_id: str | None = None
    amount: float
    allocation_type: str


class PaymentResponse(CoercedModel):
    id: str
    payment_no: str
    document_id: str | None = None
    order_id: str | None = None
    contract_id: str | None = None
    contract_no: str | None = None
    customer_id: str
    customer_name: str | None = None
    project_name: str | None = None
    department: str | None = None
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    is_voided: bool
    status_view: StatusView | None = None
    void_reason: str | None = None
    voided_at: str | None = None
    receipt_url: str | None = None
    created_at: str | None = None
    created_by: str | None = None
    allocation_status: str = "待分配"
    allocation_total: float = 0
    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PaymentVoid(BaseModel):
    void_reason: str

    @field_validator("void_reason")
    @classmethod
    def reason_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("作废原因不能为空")
        return value


class StatementCreate(BaseModel):
    customer_id: UUID
    start_date: str
    end_date: str


class StatementResponse(CoercedModel):
    id: str
    statement_no: str
    customer_id: str
    start_date: str | None = None
    end_date: str | None = None
    total_order_amount: float
    total_paid_amount: float
    total_unpaid_amount: float
    status: str
    status_view: StatusView | None = None
    capabilities: dict[str, ActionCapability] = {}
    confirmed_at: str | None = None
    confirmed_by: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class StatementDetailResponse(StatementResponse):
    orders: list["StatementOrderItem"] = []
    payments: list["StatementPaymentItem"] = []


class StatementOrderItem(CoercedModel):
    id: str
    order_no: str
    project_name: str
    status: str
    status_view: StatusView | None = None
    total_amount: float
    paid_amount: float
    unpaid_amount: float


class StatementPaymentItem(CoercedModel):
    id: str
    payment_no: str
    amount: float
    payment_method: str | None = None
    paid_at: str | None = None
    is_voided: bool


class ExpenseCreate(BaseModel):
    category: str | None = None
    payment_method: str | None = None
    # Legacy clients may continue to send amount as the source total. New
    # clients should send paid_amount + payable_amount; the service derives
    # amount from that breakdown before persistence.
    amount: float = 0
    paid_amount: float | None = None
    payee_name: str | None = None
    supplier_id: str | None = None
    payable_amount: float = 0
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("支出金额不能小于0")
        return v

    @field_validator("paid_amount")
    @classmethod
    def paid_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("支付金额不能小于0")
        return value

    @field_validator("payable_amount")
    @classmethod
    def payable_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("待付款金额不能小于0")
        return value


class ExpenseUpdate(BaseModel):
    category: str | None = None
    payment_method: str | None = None
    amount: float | None = None
    paid_amount: float | None = None
    payee_name: str | None = None
    supplier_id: str | None = None
    payable_amount: float | None = None
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("支出金额必须大于0")
        return value

    @field_validator("paid_amount")
    @classmethod
    def paid_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("支付金额不能小于0")
        return value

    @field_validator("payable_amount")
    @classmethod
    def payable_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("待付款金额不能小于0")
        return value


class ExpenseDeleteConfirmed(BaseModel):
    """确认撤销有效应付付款流水并删除经营支出时的快照。"""

    expected_payment_count: int = Field(default=0, ge=0)
    expected_paid_amount: Decimal = Field(default=Decimal("0"), ge=0)


class ExpenseResponse(CoercedModel):
    id: str
    expense_no: str
    category: str | None = None
    payment_method: str | None = None
    amount: float
    payee_name: str | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    payable_amount: float = 0
    initial_paid_amount: float = 0
    payable_paid_amount: float = 0
    total_paid_amount: float = 0
    remaining_payable_amount: float = 0
    payable_status: str = "paid"
    payable_payment_count: int = 0
    description: str | None = None
    expense_date: str | None = None
    receipt_url: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    # New unified fields
    document_id: str | None = None
    doc_no: str | None = None
    doc_type: str | None = None
    document_item_id: str | None = None
    document_item_name: str | None = None
    attachment_count: int = 0

    model_config = {"from_attributes": True}


class PayablePaymentCreate(BaseModel):
    amount: float
    payment_method: str = "转账支付"
    paid_at: str | None = None
    remark: str | None = None
    receipt_url: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("付款金额必须大于0")
        return value

    @field_validator("payment_method")
    @classmethod
    def payment_method_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("付款方式不能为空")
        return value


class PayablePaymentVoid(BaseModel):
    void_reason: str

    @field_validator("void_reason")
    @classmethod
    def reason_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("撤销原因不能为空")
        return value


class PayablePaymentResponse(CoercedModel):
    id: str
    payment_no: str
    source_type: str
    source_id: str
    amount: float
    payment_method: str
    paid_at: str | None = None
    remark: str | None = None
    receipt_url: str | None = None
    is_voided: bool = False
    void_reason: str | None = None
    voided_at: str | None = None
    created_at: str | None = None
    created_by: str | None = None


class PayableResponse(CoercedModel):
    id: str
    source_type: str
    source_id: str
    source_label: str
    source_no: str
    source_total_amount: float
    payable_total_amount: float
    paid_amount: float
    remaining_amount: float
    payee_name: str | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    status: str
    status_view: StatusView | None = None
    capabilities: dict[str, ActionCapability] = {}
    order_no: str | None = None
    quote_no: str | None = None
    project_name: str | None = None
    customer_name: str | None = None
    document_item_name: str | None = None
    category: str | None = None
    description: str | None = None
    remark: str | None = None
    payment_method: str | None = None
    source_date: str | None = None
    payments: list[PayablePaymentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Project Cost ──

class ProjectCostCreate(BaseModel):
    source_type: str = "order"
    order_id: str | None = None
    quote_id: str | None = None
    category: str
    amount: float
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    order_item_id: str | None = None
    order_item_ids: list[UUID] | None = Field(default=None, max_length=100)
    quote_item_id: str | None = None
    group_name: str | None = None
    payment_method: str | None = None
    payee_company_name: str | None = None
    supplier_id: str | None = None
    debt_amount: float | None = None
    quantity: float | None = None
    specification: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    summary: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("支出总额必须大于0")
        return v

    @field_validator("order_id", "quote_id")
    @classmethod
    def source_id_check(cls, v: str | None, info) -> str | None:
        if info.field_name == "order_id" and v is not None and not v.strip():
            raise ValueError("订单ID不能为空")
        if info.field_name == "quote_id" and v is not None and not v.strip():
            raise ValueError("报价单ID不能为空")
        return v.strip() if v else None


class ProjectCostUpdate(BaseModel):
    category: str | None = None
    amount: float | None = None
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    order_item_id: str | None = None
    quote_item_id: str | None = None
    group_name: str | None = None
    payment_method: str | None = None
    payee_company_name: str | None = None
    supplier_id: str | None = None
    source_type: str | None = None
    quote_id: str | None = None
    debt_amount: float | None = None
    quantity: float | None = None
    specification: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    summary: str | None = None
    order_item_ids: list[UUID] | None = Field(default=None, max_length=100)


class ProjectCostItemScope(CoercedModel):
    order_item_id: str
    order_item_name: str | None = None


class ProjectCostResponse(CoercedModel):
    id: str
    cost_no: str
    source_type: str = "order"
    order_id: str | None = None
    quote_id: str | None = None
    quote_no: str | None = None
    order_item_id: str | None = None
    order_item_ids: list[str] = Field(default_factory=list)
    quote_item_id: str | None = None
    order_item_name: str | None = None
    quote_item_name: str | None = None
    group_name: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    category: str
    amount: float
    payment_amount: float = 0
    payment_method: str | None = None
    payee_company_name: str | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    debt_amount: float | None = None
    quantity: float | None = None
    specification: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    summary: str | None = None
    is_debt: bool = False
    is_settled: bool = False
    settled_at: str | None = None
    description: str | None = None
    cost_date: str | None = None
    receipt_url: str | None = None
    remark: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    # New unified fields
    document_id: str | None = None
    doc_no: str | None = None
    doc_type: str | None = None
    document_item_id: str | None = None
    document_item_name: str | None = None
    item_scopes: list[ProjectCostItemScope] = Field(default_factory=list)
    scope_type: str = "document"
    attachment_count: int = 0

    model_config = {"from_attributes": True}


class DebtSettleCreate(BaseModel):
    """结算欠款"""
    settle_amount: float
    payment_method: str = "转账支付"
    remark: str | None = None

    @field_validator("settle_amount")
    @classmethod
    def amount_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("结清金额必须大于0")
        return value


class DebtResponse(CoercedModel):
    """欠款清单响应"""
    id: str
    cost_no: str
    source_type: str = "order"
    order_id: str | None = None
    quote_id: str | None = None
    order_no: str | None = None
    quote_no: str | None = None
    project_name: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    category: str
    amount: float
    quantity: float | None = None
    specification: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    payment_method: str | None = None
    payee_company_name: str | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    debt_amount: float
    is_settled: bool = False
    status_view: StatusView | None = None
    capabilities: dict[str, ActionCapability] = {}
    settled_at: str | None = None
    cost_date: str | None = None
    description: str | None = None
    remark: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    # New unified fields
    document_id: str | None = None
    doc_no: str | None = None
    doc_type: str | None = None
    document_item_id: str | None = None
    document_item_name: str | None = None
    attachment_count: int = 0

    model_config = {"from_attributes": True}
