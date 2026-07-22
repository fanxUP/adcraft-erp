import uuid

from datetime import date
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class BusinessDocument(Base, TimestampMixin, SoftDeleteMixin):
    """统—业务单据表（合并 orders & quotes）。

    按 doc_type 区分：
      - 'order'  → 订单（原 orders 表）
      - 'quote'  → 报价（原 quotes 表）

    doc_type 切换 = 订单↔报价转换，document_id 永远不变。
    """
    __tablename__ = "business_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── 鉴别器 ──
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="order | quote")

    # ── 统一编号（O-xxx = 报价, S-xxx = 订单） ──
    doc_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # ── 共享字段 ──
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 报价可仅有名称
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sales_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="部门/科室")
    contact_person: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="联系电话")

    # ── 订单专有字段（doc_type='order' 时有效） ──
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    unpaid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    cost_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    delivery_deadline: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    installation_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True,
        comment="自引用 FK：订单来源报价的 ID（原 orders.quote_id）"
    )

    # ── 报价专有字段（doc_type='quote' 时有效） ──
    subtotal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── 关系 ──
    customer: Mapped["Customer | None"] = relationship(lazy="selectin", foreign_keys=[customer_id])
    items: Mapped[list["BusinessDocumentItem"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )
    status_logs: Mapped[list["BusinessDocumentStatusLog"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )
    versions: Mapped[list["BusinessDocumentVersion"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )
    # 任务关系（仅订单有）
    design_tasks: Mapped[list["DesignTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    production_tasks: Mapped[list["ProductionTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    installation_tasks: Mapped[list["InstallationTask"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class BusinessDocumentItem(Base, TimestampMixin):
    """统一业务单据明细表（合并 order_items & quote_items）。"""
    __tablename__ = "business_document_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False
    )
    source_quote_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_document_items.id"), nullable=True
    )

    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    length: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    length_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    width: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    width_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    height: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    height_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, default="m")
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    use_area: Mapped[bool] = mapped_column(default=False)
    quantity_mode: Mapped[str] = mapped_column(String(16), default="piece")
    pieces: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, default=1, comment="件数")
    area: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    process_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    installation_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    design_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    transport_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    other_fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    subtotal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    material_process: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)

    document: Mapped["BusinessDocument"] = relationship(back_populates="items")


class BusinessDocumentStatusLog(Base):
    """统一单据状态变更日志（合并 order_status_logs，报价也可用）。"""
    __tablename__ = "business_document_status_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    operated_at: Mapped[str] = mapped_column(DateTime, nullable=False)

    document: Mapped["BusinessDocument"] = relationship(back_populates="status_logs")


class BusinessDocumentVersion(Base, TimestampMixin):
    """统一单据版本快照（替换 quote_versions）。"""
    __tablename__ = "business_document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    document: Mapped["BusinessDocument"] = relationship(back_populates="versions")
