"""高空作业车台账模块 — ORM 模型

独立于车辆管理模块，不复用 vehicles / vehicle_drivers / vehicle_cost_allocations 等表。
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Integer, Numeric, String, Text, ForeignKey, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ── 高空车档案 ──────────────────────────────────────────────────────────────

class AerialVehicle(Base, TimestampMixin):
    __tablename__ = "aerial_vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="车牌号")
    vehicle_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="车辆名称")
    brand_model: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="品牌型号")
    max_working_height: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="最大作业高度")
    platform_capacity: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="平台承重")
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="购买日期")
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False, comment="状态: available/in_use/maintenance/disabled/scrapped")
    default_personnel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_personnel.id"), nullable=True, comment="默认人员")
    insurance_expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="保险到期日")
    inspection_expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="年检到期日")
    maintenance_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="下次保养日期")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    default_personnel: Mapped["AerialPersonnel | None"] = relationship("AerialPersonnel", foreign_keys=[default_personnel_id], lazy="selectin")


# ── 高空车人员 ──────────────────────────────────────────────────────────────

class AerialPersonnel(Base, TimestampMixin):
    __tablename__ = "aerial_personnel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="人员姓名")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号")
    license_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="驾驶证号")
    license_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="驾驶证类型")
    license_expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="驾驶证到期日")
    is_external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否外协")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/disabled")
    personnel_type: Mapped[str] = mapped_column(String(32), default="driver", nullable=False, comment="人员类型: driver/assistant/operator")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


# ── 每日出车台账 ────────────────────────────────────────────────────────────

class AerialDailyLedger(Base, TimestampMixin):
    __tablename__ = "aerial_daily_ledgers"
    __table_args__ = (
        Index("ix_aerial_ledger_work_date", "work_date"),
        Index("ix_aerial_ledger_personnel_id", "personnel_id"),
        Index("ix_aerial_ledger_customer_name", "customer_name"),
        Index("ix_aerial_ledger_status", "status"),
        Index("ix_aerial_ledger_payment_status", "payment_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="台账编号")
    work_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="出车日期")
    aerial_vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_vehicles.id"), nullable=False, comment="高空车ID")
    plate_number: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="冗余车牌号")
    personnel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_personnel.id"), nullable=False, comment="人员ID")
    assistant_names: Mapped[str | None] = mapped_column(Text, nullable=True, comment="随车人员，逗号分隔")

    # 客户与项目
    customer_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="客户名称")
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="联系电话")
    related_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联订单号")
    related_task_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联安装任务号")

    # 作业信息
    work_location: Mapped[str] = mapped_column(String(256), nullable=False, comment="作业地点")
    work_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="作业类型")
    work_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作业内容")
    planned_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="计划开始")
    planned_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="计划结束")
    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际开始")
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际结束")

    # 计费与收款
    billing_method: Mapped[str] = mapped_column(String(32), default="trip", nullable=False, comment="计费方式: trip/hour/half_day/day/project/free/included_in_order")
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="单价")
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=1, nullable=False, comment="数量")
    receivable_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="应收金额")
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="优惠金额")
    final_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="最终应收")
    received_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="实收金额")
    unpaid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="未收金额")
    settlement_type: Mapped[str] = mapped_column(String(32), default="separate", nullable=False, comment="结算方式: separate/included_in_order/monthly/free")
    payment_status: Mapped[str] = mapped_column(String(32), default="unpaid", nullable=False, comment="收款状态: unpaid/partial/paid/credit/free/included_in_order")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="收款方式")
    payment_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="收款时间")
    invoice_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否开票")
    invoice_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="发票状态")

    # 里程
    start_mileage: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True, comment="出车里程")
    end_mileage: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True, comment="收车里程")
    distance_km: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True, comment="实际公里数")

    # 成本与利润
    personnel_wage_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="人员工资")
    reimbursement_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="已审核报销金额")
    vehicle_direct_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="车辆直接费用")
    gross_profit: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="毛利润(已收)")
    estimated_profit: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="预计毛利润")

    # 异常
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否异常")
    abnormal_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常说明")

    # 状态
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, comment="状态: draft/assigned/started/working/completed/returned/reviewed/settled/cancelled/abnormal")
    audit_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="审核状态: pending/approved/rejected")

    # 操作人
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="创建人")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    voided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="作废人")
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="作废时间")
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    aerial_vehicle: Mapped["AerialVehicle"] = relationship("AerialVehicle", foreign_keys=[aerial_vehicle_id], lazy="selectin")
    personnel: Mapped["AerialPersonnel"] = relationship("AerialPersonnel", foreign_keys=[personnel_id], lazy="selectin")
    expenses: Mapped[list["AerialPersonnelExpense"]] = relationship("AerialPersonnelExpense", back_populates="ledger", lazy="selectin")
    wages: Mapped[list["AerialPersonnelWage"]] = relationship("AerialPersonnelWage", back_populates="ledger", lazy="selectin")
    vehicle_costs: Mapped[list["AerialVehicleCost"]] = relationship("AerialVehicleCost", back_populates="ledger", lazy="selectin")
    safety_checks: Mapped[list["AerialSafetyCheck"]] = relationship("AerialSafetyCheck", back_populates="ledger", lazy="selectin")
    attachments: Mapped[list["AerialLedgerAttachment"]] = relationship("AerialLedgerAttachment", back_populates="ledger", lazy="selectin")
    audit_logs: Mapped[list["AerialLedgerAuditLog"]] = relationship("AerialLedgerAuditLog", back_populates="ledger", lazy="selectin")


# ── 人员垫付/报销 ────────────────────────────────────────────────────────────

class AerialPersonnelExpense(Base, TimestampMixin):
    __tablename__ = "aerial_personnel_expenses"
    __table_args__ = (
        Index("ix_aerial_expense_personnel_id", "personnel_id"),
        Index("ix_aerial_expense_expense_date", "expense_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=False, comment="关联台账")
    expense_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="费用日期")
    personnel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_personnel.id"), nullable=False, comment="人员")
    expense_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="费用类型: fuel/toll/parking/meal/temporary_repair/material/other")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, comment="金额")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="支付方式")
    paid_by_personnel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否人员垫付")
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="票据照片")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="费用说明")
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="审核状态: pending/approved/rejected")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    reimbursement_status: Mapped[str] = mapped_column(String(32), default="unpaid", nullable=False, comment="报销状态: unpaid/pending_reimbursement/reimbursed")
    reimbursed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="报销时间")
    reimbursed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="报销确认人")

    ledger: Mapped["AerialDailyLedger"] = relationship("AerialDailyLedger", back_populates="expenses", lazy="selectin")
    personnel: Mapped["AerialPersonnel"] = relationship("AerialPersonnel", foreign_keys=[personnel_id], lazy="selectin")


# ── 人员工资 ──────────────────────────────────────────────────────────────────

class AerialPersonnelWage(Base, TimestampMixin):
    __tablename__ = "aerial_personnel_wages"
    __table_args__ = (
        Index("ix_aerial_wage_personnel_id", "personnel_id"),
        Index("ix_aerial_wage_wage_month", "wage_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=True, comment="关联台账，月度汇总时可为空")
    wage_month: Mapped[str | None] = mapped_column(String(7), nullable=True, comment="工资月份 YYYY-MM")
    personnel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_personnel.id"), nullable=False, comment="人员")
    wage_type: Mapped[str] = mapped_column(String(32), default="daily", nullable=False, comment="工资类型: daily/trip/hourly/commission/base_plus_commission")
    base_wage: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="基础工资")
    trip_wage: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="趟次工资")
    hourly_wage: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="小时工资")
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="提成金额")
    allowance_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="补贴")
    deduction_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="扣款")
    final_wage_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="最终工资")
    payment_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="支付状态: pending/calculated/pending_payment/paid")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发放时间")
    paid_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="发放人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    ledger: Mapped["AerialDailyLedger | None"] = relationship("AerialDailyLedger", back_populates="wages", lazy="selectin")
    personnel: Mapped["AerialPersonnel"] = relationship("AerialPersonnel", foreign_keys=[personnel_id], lazy="selectin")


# ── 车辆费用 ────────────────────────────────────────────────────────────────

class AerialVehicleCost(Base, TimestampMixin):
    __tablename__ = "aerial_vehicle_costs"
    __table_args__ = (
        Index("ix_aerial_vcost_vehicle_id", "aerial_vehicle_id"),
        Index("ix_aerial_vcost_cost_date", "cost_date"),
        Index("ix_aerial_vcost_cost_type", "cost_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aerial_vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_vehicles.id"), nullable=False, comment="高空车ID")
    ledger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=True, comment="关联台账")
    cost_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="费用日期")
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="费用类型: fuel/maintenance/insurance/inspection/violation/tire/hydraulic_system/boom_repair/platform_repair/safety_equipment/tool_consumables/parking/loan/depreciation/other")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, comment="金额")
    handler_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="经办人")
    payer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="付款人")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="支付方式")
    is_personnel_advance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否人员垫付")
    need_reimbursement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要报销")
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="票据照片")
    allocation_type: Mapped[str] = mapped_column(String(32), default="none", nullable=False, comment="分摊方式: per_trip/daily/monthly/annual/none")
    allocation_month: Mapped[str | None] = mapped_column(String(7), nullable=True, comment="分摊月份 YYYY-MM")
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="审核状态: pending/approved/rejected")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    aerial_vehicle: Mapped["AerialVehicle"] = relationship("AerialVehicle", foreign_keys=[aerial_vehicle_id], lazy="selectin")
    ledger: Mapped["AerialDailyLedger | None"] = relationship("AerialDailyLedger", back_populates="vehicle_costs", lazy="selectin")
    payer: Mapped["AerialPersonnel | None"] = relationship(
        "AerialPersonnel",
        primaryjoin="AerialVehicleCost.payer_id == AerialPersonnel.id",
        foreign_keys=[payer_id],
        lazy="selectin",
    )


# ── 安全检查 ────────────────────────────────────────────────────────────────

class AerialSafetyCheck(Base):
    __tablename__ = "aerial_safety_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=False, comment="关联台账")
    check_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="检查类型: before_work/after_work")
    checker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="检查人")
    vehicle_appearance_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="车辆外观")
    tire_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="轮胎")
    brake_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="刹车")
    light_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="灯光")
    hydraulic_system_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="液压系统")
    outriggers_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="支腿")
    platform_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="作业平台")
    safety_belt_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="安全带/安全绳")
    warning_equipment_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="警示设备")
    extinguisher_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="灭火器")
    documents_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="证件有效")
    weather_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="天气适宜")
    site_risk_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="现场安全")
    issue_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常说明")
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True, comment="检查照片JSON")
    check_result: Mapped[str] = mapped_column(String(32), default="passed", nullable=False, comment="检查结果: passed/failed/need_attention")
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="检查时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    ledger: Mapped["AerialDailyLedger"] = relationship("AerialDailyLedger", back_populates="safety_checks", lazy="selectin")


# ── 台账附件 ────────────────────────────────────────────────────────────────

class AerialLedgerAttachment(Base):
    __tablename__ = "aerial_ledger_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=False, comment="关联台账")
    attachment_type: Mapped[str] = mapped_column(String(32), default="other", nullable=False, comment="附件类型: site_photo/completion_photo/receipt/invoice/safety_photo/issue_photo/other")
    file_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件URL")
    file_name: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="文件名")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="上传人")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="上传时间")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    ledger: Mapped["AerialDailyLedger"] = relationship("AerialDailyLedger", back_populates="attachments", lazy="selectin")


# ── 审计日志 ────────────────────────────────────────────────────────────────

class AerialLedgerAuditLog(Base):
    __tablename__ = "aerial_ledger_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=True, comment="关联台账")
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="操作人")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作类型")
    source: Mapped[str] = mapped_column(String(32), default="erp", nullable=False, comment="来源: erp/wechat_agent/feishu_agent/system")
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="操作对象类型")
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="操作对象ID")
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作前JSON")
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作后JSON")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    ledger: Mapped["AerialDailyLedger | None"] = relationship("AerialDailyLedger", back_populates="audit_logs", lazy="selectin")


# ── Agent 草稿 ──────────────────────────────────────────────────────────────

class AerialAgentDraft(Base):
    """Agent 识别消息后生成的草稿，人工确认后才写入正式台账"""
    __tablename__ = "aerial_agent_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 消息来源
    platform: Mapped[str] = mapped_column(String(32), nullable=False, comment="来源平台: wechat/workbuddy/feishu/erp")
    conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="会话ID")
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="消息ID")
    sender_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="发送人ID")
    sender_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="发送人名称")
    raw_message: Mapped[str] = mapped_column(Text, nullable=False, comment="原始消息内容")
    # 识别结果
    intent: Mapped[str] = mapped_column(String(64), nullable=False, comment="识别意图: aerial_work_ledger/aerial_driver_expense/aerial_payment_claim/aerial_vehicle_issue/aerial_query_report/aerial_reimbursement_claim/normal_chat")
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False, comment="置信度 0-1")
    risk_level: Mapped[str] = mapped_column(String(16), default="low", nullable=False, comment="风险等级: low/medium/high")
    extracted_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="提取的结构化数据JSON")
    suggested_action: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="建议动作")
    # 状态管理
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="草稿状态: pending/confirmed/rejected/expired")
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="确认人")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="确认时间")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="拒绝原因")
    # 执行结果
    created_ledger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_daily_ledgers.id"), nullable=True, comment="生成的台账ID")
    created_expense_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_personnel_expenses.id"), nullable=True, comment="生成的垫付ID")
    created_cost_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("aerial_vehicle_costs.id"), nullable=True, comment="生成的车辆费用ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
