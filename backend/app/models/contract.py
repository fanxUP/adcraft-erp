import uuid

from datetime import datetime
from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.customer import Customer
from app.models.order import Order
from app.models.quote import Quote


class Contract(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # 客户
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 项目
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 金额
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    unpaid_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    # 日期
    sign_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 签约方
    our_signatory: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="我方签约人")
    customer_signatory: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="客户签约人")

    # 合同类型：制作合同、安装合同、综合合同等
    contract_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(64), default="draft")

    # 内容 / 备注
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="合同条款内容")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 合同原件
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="合同原件存储路径")
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="合同原件文件名")

    # 创建人
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 关系
    customer: Mapped["Customer"] = relationship(lazy="selectin")
    orders: Mapped[list["Order"]] = relationship(
        secondary="contract_orders", lazy="selectin"
    )
    quotes: Mapped[list["Quote"]] = relationship(
        secondary="contract_quotes", lazy="selectin"
    )


class ContractOrder(Base, TimestampMixin):
    __tablename__ = "contract_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )


class ContractQuote(Base, TimestampMixin):
    __tablename__ = "contract_quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False
    )
