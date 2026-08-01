"""CDR 智能报价——Pydantic 请求/响应模型。"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
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
    # Phase 7 几何参数
    hole_area_mm2: Decimal | None = Field(None, max_digits=16, decimal_places=3)
    is_open_curve: bool = False
    curve_length_mm: Decimal | None = Field(None, max_digits=16, decimal_places=3)
    use_sheet_rounding: bool = False
    sheet_width_mm: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    sheet_height_mm: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    sheet_sale_price: Decimal | None = Field(None, max_digits=14, decimal_places=2)
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
    # Phase 7
    geometry_estimates: dict | None = None
    sheet_usage: dict | None = None
    warnings: list[str] = []
    pricing_trace: list[PriceTraceStep] = []


# ── 报价行 ──────────────────────────────────────────────────────

# ── 几何分析 ──────────────────────────────────────────────────


class QuoteGeometryResponse(BaseModel):
    id: UUID
    quote_line_id: UUID | None = None
    quote_id: UUID | None = None
    net_area_mm2: Decimal | None = None
    hole_area_mm2: Decimal | None = None
    curve_length_mm: Decimal | None = None
    is_open_curve: bool = False
    overlap_count: int | None = None
    overlap_area_mm2: Decimal | None = None
    sheet_count: int | None = None
    sheet_utilization_pct: Decimal | None = None
    is_estimated: bool = True
    nesting_json: dict | None = None
    analysis_json: dict | None = None


class GeometryAnalyzeRequest(BaseModel):
    width_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    height_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    holes: list[dict] = []


class GeometryAnalyzeResponse(BaseModel):
    bbox_area_mm2: Decimal | None = None
    hole_area_mm2: Decimal | None = None
    net_area_mm2: Decimal | None = None
    hole_ratio: Decimal | None = None
    is_estimated: bool = True
    error: str | None = None


class NestingRequest(BaseModel):
    rects: list[dict] = []
    sheet_width_mm: Decimal
    sheet_height_mm: Decimal


class NestingItem(BaseModel):
    id: str
    x: Decimal
    y: Decimal
    w: Decimal
    h: Decimal
    rotated: bool = False


class NestingSheet(BaseModel):
    sheet_no: int
    items: list[NestingItem] = []


class NestingResponse(BaseModel):
    sheets: list[NestingSheet] = []
    total_sheets: int = 0
    total_pieces: int = 0
    utilization_pct: Decimal = Decimal("0")
    is_estimated: bool = True
    error: str | None = None


class QuoteLineProcessCreate(BaseModel):
    process_id: UUID
    billing_quantity: Decimal = Field(default=Decimal("1"), max_digits=14, decimal_places=4)
    unit: str | None = None
    unit_price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)


class QuoteLineCreate(BaseModel):
    product_id: UUID | None = None
    material_id: UUID | None = None
    item_name: str | None = Field(None, min_length=1)
    description: str | None = Field(None, min_length=1)
    material_process: str | None = None
    width: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    width_unit: str | None = "m"
    height: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    height_unit: str | None = "m"
    width_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    height_mm: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    length_m: Decimal | None = Field(None, max_digits=12, decimal_places=3)
    quantity: Decimal = Field(default=Decimal("1"), max_digits=14, decimal_places=3)
    unit: str | None = None
    use_area: bool = False
    pieces: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)
    process_fee: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    installation_fee: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    design_fee: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    transport_fee: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    other_fee: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    remark: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    group_name: str | None = None
    manual_adjustment: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    manual_reason: str | None = None
    processes: list[QuoteLineProcessCreate] = []

    @model_validator(mode="after")
    def synchronize_item_name(self):
        name = self.item_name or self.description
        if not name:
            raise ValueError("请填写项目内容")
        self.item_name = name
        self.description = name
        return self


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
    item_name: str
    description: str
    material_process: str | None
    width: Decimal | None
    width_unit: str | None
    height: Decimal | None
    height_unit: str | None
    width_mm: Decimal | None
    height_mm: Decimal | None
    length_m: Decimal | None
    quantity: Decimal
    unit: str | None
    use_area: bool
    pieces: Decimal | None
    billable_quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    estimated_cost: Decimal
    process_fee: Decimal
    installation_fee: Decimal
    design_fee: Decimal
    transport_fee: Decimal
    other_fee: Decimal
    remark: str | None
    image_url: str | None
    sort_order: int
    group_name: str | None
    manual_adjustment: Decimal
    manual_reason: str | None
    source: str
    requires_approval: bool
    pricing_trace_json: dict | None
    created_at: datetime | None = None
    geometry: QuoteGeometryResponse | None = None
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


# ── Phase 8: AI报价助手 ──────────────────────────────────────────


class ProcessGapItem(BaseModel):
    type: str = "process_gap"
    severity: str = "info"
    line_id: UUID | None = None
    line_no: int | None = None
    line_desc: str = ""
    missing_process_name: str = ""
    missing_process_id: UUID | None = None
    reason: str = ""


class ProcessGapResponse(BaseModel):
    mode: str = "rule_based"
    gaps: list[ProcessGapItem] = []
    gap_count: int = 0
    summary: dict = {}


class QuoteDescriptionRequest(BaseModel):
    version_id: UUID | None = None
    customer_id: UUID | None = None
    lead_days: int | None = None
    warranty_months: int | None = None
    deposit_pct: int | None = None
    payment_terms: str | None = None
    delivery_address: str | None = None
    tax_rate: Decimal | None = None


class QuoteDescriptionResponse(BaseModel):
    description: str = ""
    sections: dict = {}
    summary: dict = {}


class PriceAnomalyItem(BaseModel):
    type: str = ""
    severity: str = "info"
    line_no: int | None = None
    title: str = ""
    detail: str = ""
    suggestion: str = ""
    current_price: float | None = None
    historical_avg: float | None = None
    deviation_pct: float | None = None


class PriceAnomalyResponse(BaseModel):
    mode: str = "rule_based"
    anomalies: list[PriceAnomalyItem] = []
    anomaly_count: int = 0
    summary: dict = {}


class DeviationSummary(BaseModel):
    estimated_amount: float = 0
    estimated_cost: float = 0
    estimated_margin_pct: float = 0
    total_items: int = 0
    has_production_data: bool = False
    quote_converted: bool = False
    order_id: str | None = None
    order_no: str | None = None
    actual_amount: float | None = None
    actual_cost: float | None = None
    deviation_amount: float | None = None
    deviation_pct: float | None = None


class DeviationLineItem(BaseModel):
    line_no: int | None = None
    description: str = ""
    estimated: dict = {}
    actual: dict | None = None
    deviation: dict | None = None
    no_production_data: bool = True


class DeviationResponse(BaseModel):
    quote_id: str = ""
    quote_no: str = ""
    project_name: str = ""
    summary: DeviationSummary = DeviationSummary()
    items: list[DeviationLineItem] = []
