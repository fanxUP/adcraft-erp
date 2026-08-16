"""CDR 智能报价——新增领域模型。

设计原则：
- 复用现有 customers、business_documents(作为报价 header)、users 等表
- 报价版本/明细/审批/审计独立建表，不与现有 BusinessDocumentItem 耦合
- 金额全部使用 NUMERIC，禁止 float
- 每次报价快照保存规则版本、价格快照、图稿摘要
"""

import uuid
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


# ── 1. 定价规则引擎 ─────────────────────────────────────────────


class PriceRuleSet(Base, TimestampMixin):
    """定价规则集——分组和版本控制。"""
    __tablename__ = "price_rule_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft", comment="draft | published | archived")
    effective_from: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="YYYY-MM-DD")
    effective_to: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="YYYY-MM-DD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rules: Mapped[list["CdrPriceRule"]] = relationship(back_populates="rule_set", lazy="selectin", cascade="all, delete-orphan")


class CdrPriceRule(Base, TimestampMixin):
    """定价规则——触发条件 + 计算动作。"""
    __tablename__ = "cdr_price_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_rule_sets.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    conditions_json: Mapped[dict] = mapped_column(JSONB, default=dict, comment="触发条件列表")
    actions_json: Mapped[dict] = mapped_column(JSONB, default=dict, comment="计算动作列表")
    conflict_policy: Mapped[str] = mapped_column(String(32), default="higher_priority_wins", comment="冲突策略")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    rule_set: Mapped["PriceRuleSet"] = relationship(back_populates="rules")


# ── 2. 客户协议价 ───────────────────────────────────────────────


class CustomerPriceAgreement(Base, TimestampMixin):
    """客户专项价格协议。"""
    __tablename__ = "customer_price_agreements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    pricing_method: Mapped[str] = mapped_column(String(32), nullable=False, comment="area | length | quantity | fixed")
    price_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    minimum_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=1.0, comment="折扣率：0.8=打8折")
    effective_from: Mapped[str] = mapped_column(String(32), nullable=False, comment="YYYY-MM-DD")
    effective_to: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="YYYY-MM-DD")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── 3. 报价核心 ─────────────────────────────────────────────────


class QuoteVersion(Base, TimestampMixin):
    """报价版本——每次保存生成新版本，历史版本不可修改。

    关联 quotes 作为报价 header，
    该表存储版本快照和明细。
    """
    __tablename__ = "quote_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    pricing_rule_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_rule_sets.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", comment="draft | review | approved | rejected")

    # 金额汇总
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estimated_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estimated_margin: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)

    # 快照
    snapshot_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="报价快照（客户/产品/价格快照）")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 关系
    lines: Mapped[list["QuoteLine"]] = relationship(back_populates="version", lazy="selectin", cascade="all, delete-orphan")


class QuoteLine(Base, TimestampMixin):
    """报价明细行。"""
    __tablename__ = "quote_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_versions.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)

    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    material_process: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 几何/数量
    width: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    width_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    height_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    height_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    length_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    use_area: Mapped[bool] = mapped_column(Boolean, default=False)
    pieces: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="件数")

    # 计费
    billable_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0, comment="计费数量（含损耗）")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    process_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    installation_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    design_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    transport_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    other_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 手工调整
    manual_adjustment: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    manual_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="auto", comment="auto | manual")

    # 审批标记
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    # 价格执行明细
    pricing_trace_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="规则执行过程")

    version: Mapped["QuoteVersion"] = relationship(back_populates="lines")
    processes: Mapped[list["QuoteLineProcess"]] = relationship(back_populates="line", lazy="selectin", cascade="all, delete-orphan")


class QuoteLineProcess(Base, TimestampMixin):
    """报价行工艺明细。"""
    __tablename__ = "quote_line_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_lines.id"), nullable=False)
    process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=False)
    billing_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pricing_trace_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    line: Mapped["QuoteLine"] = relationship(back_populates="processes")


# ── 4. 审批与审计 ───────────────────────────────────────────────


class QuoteApproval(Base, TimestampMixin):
    """报价审批记录。"""
    __tablename__ = "quote_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False)
    quote_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_versions.id"), nullable=True)
    approval_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="low_margin | over_discount | price_override | high_value")
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", comment="pending | approved | rejected")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="请求原因")
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuoteAuditLog(Base):
    """报价审计日志。"""
    __tablename__ = "quote_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False)
    quote_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_versions.id"), nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cdr_devices.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── 5. CDR 设备与图稿采集 ────────────────────────────────────────


class CdrDevice(Base, TimestampMixin):
    """CDR 插件注册设备。"""
    __tablename__ = "cdr_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    machine_fingerprint_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    plugin_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bridge_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coreldraw_versions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", comment="active | revoked")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CdrCaptureSession(Base, TimestampMixin):
    """图稿采集会话——CDR 插件每次"发送到 ERP"创建一条。"""
    __tablename__ = "cdr_capture_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cdr_devices.id"), nullable=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    document_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_path_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    coreldraw_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_index: Mapped[int] = mapped_column(Integer, default=0)
    page_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selection_count: Mapped[int] = mapped_column(Integer, default=0)
    drawing_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capture_payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DrawingSnapshot(Base, TimestampMixin):
    """图稿快照——报价确认/转订单时冻结的图稿摘要。"""
    __tablename__ = "drawing_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    capture_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cdr_capture_sessions.id"), nullable=True)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True)
    quote_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quote_versions.id"), nullable=True)
    drawing_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geometry_summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="几何摘要：宽高/面积/长度")
    object_summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="对象摘要：数量/类型分布")
    preview_file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

class QuoteGeometry(Base, TimestampMixin):
    """报价行几何分析——孔洞/重叠/曲线/板材套料数据。

    每个报价明细行一条记录，存储几何分析结果。
    is_estimated=True 表示该值是基于算法估算，非精确测量值。
    """
    __tablename__ = "quote_geometry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_lines.id"), nullable=True, unique=True,
        comment="关联报价明细行"
    )
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True,
        comment="关联报价 header（便于查询）"
    )

    # ── 孔洞与净面积 ──
    net_area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True, comment="净面积（包围盒-孔洞）mm²")
    hole_area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True, comment="孔洞总面积 mm²")

    # ── 曲线信息 ──
    curve_length_mm: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True, comment="曲线/轮廓长度 mm")
    is_open_curve: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否开放曲线")

    # ── 重叠检测 ──
    overlap_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="检测到的重叠对象数")
    overlap_area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True, comment="重叠区域估计面积 mm²")

    # ── 板材套料 ──
    sheet_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="预估需用板材张数")
    sheet_utilization_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True, comment="板材利用率（%）")
    sheet_width_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="使用的板材宽 mm（从 material 快照）")
    sheet_height_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="使用的板材高 mm")

    # ── 标记 ──
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否为估算值（非精确测量）")

    # ── 完整数据 ──
    nesting_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="排版布局结果")
    analysis_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="完整几何分析明细")
