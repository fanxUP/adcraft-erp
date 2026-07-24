"""高空作业车台账模块 — Pydantic Schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── 高空车档案 ──────────────────────────────────────────────────────────────

class AerialVehicleCreate(BaseModel):
    plate_number: str
    vehicle_name: str
    brand_model: Optional[str] = None
    max_working_height: Optional[str] = None
    platform_capacity: Optional[str] = None
    purchase_date: Optional[datetime] = None
    status: str = "available"
    default_driver_id: Optional[str] = None
    insurance_expire_date: Optional[datetime] = None
    inspection_expire_date: Optional[datetime] = None
    maintenance_due_date: Optional[datetime] = None
    remark: Optional[str] = None


class AerialVehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    vehicle_name: Optional[str] = None
    brand_model: Optional[str] = None
    max_working_height: Optional[str] = None
    platform_capacity: Optional[str] = None
    purchase_date: Optional[datetime] = None
    status: Optional[str] = None
    default_driver_id: Optional[str] = None
    insurance_expire_date: Optional[datetime] = None
    inspection_expire_date: Optional[datetime] = None
    maintenance_due_date: Optional[datetime] = None
    remark: Optional[str] = None


# ── 驾驶员 ──────────────────────────────────────────────────────────────────

class AerialDriverCreate(BaseModel):
    driver_name: str
    phone: Optional[str] = None
    license_no: Optional[str] = None
    license_type: Optional[str] = None
    license_expire_date: Optional[datetime] = None
    is_external: bool = False
    status: str = "active"
    remark: Optional[str] = None


class AerialDriverUpdate(BaseModel):
    driver_name: Optional[str] = None
    phone: Optional[str] = None
    license_no: Optional[str] = None
    license_type: Optional[str] = None
    license_expire_date: Optional[datetime] = None
    is_external: Optional[bool] = None
    status: Optional[str] = None
    remark: Optional[str] = None


# ── 每日出车台账 ────────────────────────────────────────────────────────────

class AerialLedgerCreate(BaseModel):
    work_date: datetime
    aerial_vehicle_id: str
    driver_id: str
    assistant_names: Optional[str] = None
    customer_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    related_order_no: Optional[str] = None
    related_task_no: Optional[str] = None
    work_location: str
    work_type: Optional[str] = None
    work_content: Optional[str] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    billing_method: str = "trip"
    unit_price: float = 0
    quantity: float = 1
    receivable_amount: float = 0
    discount_amount: float = 0
    final_amount: Optional[float] = None
    received_amount: float = 0
    settlement_type: str = "separate"
    payment_status: str = "unpaid"
    payment_method: Optional[str] = None
    payment_time: Optional[datetime] = None
    invoice_required: bool = False
    invoice_status: Optional[str] = None
    start_mileage: Optional[float] = None
    end_mileage: Optional[float] = None
    driver_wage_amount: float = 0
    remark: Optional[str] = None


class AerialLedgerUpdate(BaseModel):
    work_date: Optional[datetime] = None
    aerial_vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    assistant_names: Optional[str] = None
    customer_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    related_order_no: Optional[str] = None
    related_task_no: Optional[str] = None
    work_location: Optional[str] = None
    work_type: Optional[str] = None
    work_content: Optional[str] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    billing_method: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: Optional[float] = None
    receivable_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    final_amount: Optional[float] = None
    received_amount: Optional[float] = None
    settlement_type: Optional[str] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_time: Optional[datetime] = None
    invoice_required: Optional[bool] = None
    invoice_status: Optional[str] = None
    start_mileage: Optional[float] = None
    end_mileage: Optional[float] = None
    driver_wage_amount: Optional[float] = None
    abnormal_flag: Optional[bool] = None
    abnormal_description: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


# ── 驾驶员垫付 ──────────────────────────────────────────────────────────────

class AerialDriverExpenseCreate(BaseModel):
    ledger_id: str
    expense_date: datetime
    driver_id: str
    expense_type: str
    amount: float
    payment_method: Optional[str] = None
    paid_by_driver: bool = True
    receipt_url: Optional[str] = None
    description: Optional[str] = None


class AerialDriverExpenseUpdate(BaseModel):
    expense_date: Optional[datetime] = None
    expense_type: Optional[str] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    paid_by_driver: Optional[bool] = None
    receipt_url: Optional[str] = None
    description: Optional[str] = None


class AerialExpenseReview(BaseModel):
    status: str  # approved / rejected
    remark: Optional[str] = None


class AerialExpenseReimburse(BaseModel):
    remark: Optional[str] = None


# ── 驾驶员工资 ──────────────────────────────────────────────────────────────

class AerialDriverWageCreate(BaseModel):
    ledger_id: Optional[str] = None
    wage_month: Optional[str] = None
    driver_id: str
    wage_type: str = "daily"
    base_wage: float = 0
    trip_wage: float = 0
    hourly_wage: float = 0
    commission_amount: float = 0
    allowance_amount: float = 0
    deduction_amount: float = 0
    final_wage_amount: float = 0
    remark: Optional[str] = None


class AerialDriverWageUpdate(BaseModel):
    wage_type: Optional[str] = None
    base_wage: Optional[float] = None
    trip_wage: Optional[float] = None
    hourly_wage: Optional[float] = None
    commission_amount: Optional[float] = None
    allowance_amount: Optional[float] = None
    deduction_amount: Optional[float] = None
    final_wage_amount: Optional[float] = None
    payment_status: Optional[str] = None
    remark: Optional[str] = None


# ── 车辆费用 ────────────────────────────────────────────────────────────────

class AerialVehicleCostCreate(BaseModel):
    aerial_vehicle_id: str
    ledger_id: Optional[str] = None
    cost_date: datetime
    cost_type: str
    amount: float
    handler_id: Optional[str] = None
    payer_id: Optional[str] = None
    payment_method: Optional[str] = None
    is_driver_advance: bool = False
    need_reimbursement: bool = False
    receipt_url: Optional[str] = None
    allocation_type: str = "none"
    allocation_month: Optional[str] = None
    remark: Optional[str] = None


class AerialVehicleCostUpdate(BaseModel):
    cost_date: Optional[datetime] = None
    cost_type: Optional[str] = None
    amount: Optional[float] = None
    handler_id: Optional[str] = None
    payer_id: Optional[str] = None
    payment_method: Optional[str] = None
    is_driver_advance: Optional[bool] = None
    need_reimbursement: Optional[bool] = None
    receipt_url: Optional[str] = None
    allocation_type: Optional[str] = None
    allocation_month: Optional[str] = None
    remark: Optional[str] = None


class AerialCostReview(BaseModel):
    status: str  # approved / rejected
    remark: Optional[str] = None


# ── 安全检查 ────────────────────────────────────────────────────────────────

class AerialSafetyCheckCreate(BaseModel):
    ledger_id: str
    check_type: str  # before_work / after_work
    checker_id: Optional[str] = None
    vehicle_appearance_ok: bool = True
    tire_ok: bool = True
    brake_ok: bool = True
    light_ok: bool = True
    hydraulic_system_ok: bool = True
    outriggers_ok: bool = True
    platform_ok: bool = True
    safety_belt_ok: bool = True
    warning_equipment_ok: bool = True
    extinguisher_ok: bool = True
    documents_ok: bool = True
    weather_ok: bool = True
    site_risk_ok: bool = True
    issue_description: Optional[str] = None
    photo_urls: Optional[str] = None
    check_result: str = "passed"


# ── 附件 ────────────────────────────────────────────────────────────────────

class AerialAttachmentCreate(BaseModel):
    ledger_id: str
    attachment_type: str = "other"
    file_url: str
    file_name: Optional[str] = None
    remark: Optional[str] = None


# ── 审计日志 ────────────────────────────────────────────────────────────────

class AerialAuditLogQuery(BaseModel):
    ledger_id: Optional[str] = None
    action: Optional[str] = None
    source: Optional[str] = None


# ── Agent 草稿 ──────────────────────────────────────────────────────────────

class AerialAgentMessageIngest(BaseModel):
    """Agent 消息接入请求"""
    platform: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    message_type: str = "text"
    content: str
    attachments: Optional[list] = []
    sent_at: Optional[str] = None

class AerialAgentDraftOut(BaseModel):
    """Agent 草稿输出"""
    id: str
    platform: str
    conversation_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    raw_message: str
    intent: str
    confidence: float
    risk_level: str
    extracted: Optional[dict] = None
    suggested_action: Optional[str] = None
    status: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    reject_reason: Optional[str] = None
    created_ledger_id: Optional[str] = None
    created_expense_id: Optional[str] = None
    created_cost_id: Optional[str] = None
    created_at: str

class AerialAgentDraftConfirm(BaseModel):
    """确认草稿请求"""
    adjustments: Optional[dict] = None  # 人工调整的字段

class AerialAgentDraftReject(BaseModel):
    """拒绝草稿请求"""
    reason: Optional[str] = None
