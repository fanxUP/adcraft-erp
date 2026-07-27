"""CDR 智能报价——Pydantic 请求/响应模型。"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID


# ── 试算 ────────────────────────────────────────────────────────


class PricingCalculateRequest(BaseModel):
    customer_id: UUID | None = None
    product_id: UUID
    material_id: UUID | None = None
    quantity: Decimal = Field(default=Decimal("1"), max_digits=14, decimal_places=3)
    width_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    height_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    length_m: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    process_ids: list[UUID] = []


class PriceTraceStep(BaseModel):
    rule_code: str
    description: str
    input_value: dict | None = None
    output_value: dict | None = None


class PricingCalculateResponse(BaseModel):
    billable_quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    estimated_cost: Decimal = Decimal("0")
    minimum_charge_applied: bool = False
    requires_approval: bool = False
    warnings: list[str] = []
    pricing_trace: list[PriceTraceStep] = []


# ── 报价行 ──────────────────────────────────────────────────────


class QuoteLineProcessCreate(BaseModel):
    process_id: UUID
    billing_quantity: Decimal = Field(default=Decimal("1"), max_digits=14, decimal_places=4)
    unit: str | None = None
    unit_price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)


class QuoteLineCreate(BaseModel):
    product_id: UUID | None = None
    material_id: UUID | None = None
    description: str = Field(..., min_length=1)
    width_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    height_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    length_m: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    quantity: Decimal = Field(default=Decimal("1"), max_digits=14, decimal_places=3)
    unit: str | None = None
    pieces: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)
    manual_adjustment: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    manual_reason: str | None = None
    processes: list[QuoteLineProcessCreate] = []


class QuoteLineUpdate(BaseModel):
    product_id: UUID | None = None
    material_id: UUID | None = None
    description: str | None = None
    width_mm: Decimal | None = None
    height_mm: Decimal | None = None
    length_m: Decimal | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    pieces: Decimal | None = None
    unit_price: Decimal | None = None
    manual_adjustment: Decimal | None = None
    manual_reason: str | None = None


# ── 报价版本 ────────────────────────────────────────────────────


class QuoteVersionCreate(BaseModel):
    pricing_rule_set_id: UUID | None = None
    notes: str | None = None
    lines: list[QuoteLineCreate] = []


class QuoteVersionResponse(BaseModel):
    id: UUID
    quote_id: UUID
    version_no: int
    status: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    estimated_cost: Decimal
    estimated_profit: Decimal
    estimated_margin: Decimal
    notes: str | None
    created_by: UUID | None
    created_at: datetime | None = None
    lines: list["QuoteLineResponse"] = []


class QuoteLineResponse(BaseModel):
    id: UUID
    version_id: UUID
    line_no: int
    product_id: UUID | None
    material_id: UUID | None
    description: str
    width_mm: Decimal | None
    height_mm: Decimal | None
    length_m: Decimal | None
    quantity: Decimal
    unit: str | None
    pieces: Decimal | None
    billable_quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    estimated_cost: Decimal
    manual_adjustment: Decimal
    manual_reason: str | None
    source: str
    requires_approval: bool
    pricing_trace_json: dict | None
    created_at: datetime | None = None
    processes: list["QuoteLineProcessResponse"] = []


class QuoteLineProcessResponse(BaseModel):
    id: UUID
    line_id: UUID
    process_id: UUID
    billing_quantity: Decimal
    unit: str | None
    unit_price: Decimal
    amount: Decimal
    cost_amount: Decimal
    pricing_trace_json: dict | None


# ── CDR 设备与采集 ──────────────────────────────────────────────


class CdrDeviceCreate(BaseModel):
    device_code: str
    device_name: str | None = None
    employee_id: UUID | None = None
    machine_fingerprint_hash: str


class CdrCaptureSessionCreate(BaseModel):
    device_code: str
    document_name: str | None = None
    page_index: int = 0
    page_name: str | None = None
    selection_count: int = 0
    drawing_fingerprint: str | None = None
    capture_payload: dict | None = None
    warnings: dict | None = None


# ── 客户协议价 ──────────────────────────────────────────────────


class CustomerPriceAgreementCreate(BaseModel):
    customer_id: UUID
    product_id: UUID | None = None
    material_id: UUID | None = None
    process_id: UUID | None = None
    pricing_method: str = "quantity"
    price_value: Decimal = Field(..., max_digits=14, decimal_places=4)
    minimum_charge: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    discount_rate: Decimal = Field(default=Decimal("1"), max_digits=8, decimal_places=4)
    effective_from: str
    effective_to: str | None = None
    remark: str | None = None


class CustomerPriceAgreementResponse(BaseModel):
    id: UUID
    customer_id: UUID
    product_id: UUID | None
    material_id: UUID | None
    process_id: UUID | None
    pricing_method: str
    price_value: Decimal
    minimum_charge: Decimal
    discount_rate: Decimal
    effective_from: str
    effective_to: str | None
    remark: str | None
    created_at: datetime | None = None


# ── 审批 ────────────────────────────────────────────────────────


class QuoteApprovalCreate(BaseModel):
    approval_type: str
    reason: str | None = None


class QuoteApprovalResponse(BaseModel):
    id: UUID
    quote_id: UUID
    quote_version_id: UUID | None
    approval_type: str
    requested_by: UUID
    approver_id: UUID | None
    status: str
    reason: str | None
    decision_comment: str | None
    created_at: datetime | None = None
    decided_at: datetime | None = None


# ── 规则集/规则 ─────────────────────────────────────────────────


class PriceRuleCreate(BaseModel):
    code: str
    name: str
    priority: int = 0
    conditions_json: dict = {}
    actions_json: dict = {}
    conflict_policy: str = "higher_priority_wins"


class PriceRuleSetCreate(BaseModel):
    code: str
    name: str
    effective_from: str | None = None
    effective_to: str | None = None
    description: str | None = None
    rules: list[PriceRuleCreate] = []


class PriceRuleSetResponse(BaseModel):
    id: UUID
    code: str
    name: str
    version: int
    status: str
    effective_from: str | None
    effective_to: str | None
    description: str | None
    published_by: UUID | None
    published_at: datetime | None
    created_at: datetime | None = None
    rules: list["PriceRuleResponse"] = []


class PriceRuleResponse(BaseModel):
    id: UUID
    rule_set_id: UUID
    code: str
    name: str
    priority: int
    conditions_json: dict
    actions_json: dict
    conflict_policy: str
    active: bool
    created_at: datetime | None = None
