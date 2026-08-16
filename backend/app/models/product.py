import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_categories.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    material_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    process_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="项")
    pricing_method: Mapped[str] = mapped_column(String(64), default="quantity")
    default_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    min_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # CDR 智能报价扩展字段
    requires_geometry: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要 CDR 几何数据")
    needs_installation: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要安装")
    allows_outsource: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否允许外协")
    needs_approval: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要审批")
    default_loss_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, comment="默认损耗率")
    standard_lead_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="标准交期（天）")

    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    spec: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="材料分类：板材/卷材/辅材等")
    unit: Mapped[str] = mapped_column(String(32), default="张")
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    loss_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    safe_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)

    # CDR 扩展字段
    thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True, comment="厚度(mm)")
    sheet_width_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="单张/单卷宽度(mm)")
    sheet_height_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="单张/单卷高度(mm)")
    purchase_unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="采购单位")
    min_purchase_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, comment="最小采购量")
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="默认供应商")
    price_updated_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="上次调价时间")

    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Process(Base, TimestampMixin):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    charge_method: Mapped[str] = mapped_column(String(64), default="fixed")
    default_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    billing_basis: Mapped[str] = mapped_column(String(32), default="fixed", comment="计价基准: area/length/quantity/hours/fixed")
    machine_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="设备类型")
    startup_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, comment="开机费")
    min_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, comment="最低收费")
    standard_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True, comment="标准人工工时")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceRule(Base, TimestampMixin):
    __tablename__ = "price_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    process_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=True)
    pricing_method: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    min_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    formula: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MaterialPriceVersion(Base, TimestampMixin):
    """材料价格版本——价格变更记录，历史报价可追溯。"""
    __tablename__ = "material_price_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price_type: Mapped[str] = mapped_column(String(32), default="purchase", comment="purchase|sale")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    tax_included: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    effective_from: Mapped[str] = mapped_column(String(32), nullable=False, comment="YYYY-MM-DD")
    effective_to: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="YYYY-MM-DD")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
