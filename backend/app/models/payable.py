"""应付付款流水。

应付记录不重复保存一笔支出，而是通过 ``source_type``/``source_id``
指向支出来源。付款流水是新付款状态的事实来源；项目成本上的旧字段
只作为历史兼容字段保留。
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PayablePayment(Base, TimestampMixin):
    """一笔应付付款流水，不与客户收款 ``payments`` 混用。

    ``source_type``/``source_id`` 是多来源关联，不使用多态外键，以便
    普通支出、项目成本以及后续外协/车辆应付都能接入同一付款流水表。
    """

    __tablename__ = "payable_payments"
    __table_args__ = (
        Index("ix_payable_payments_source", "source_type", "source_id", "paid_at"),
        Index("ix_payable_payments_active", "is_voided", "paid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="来源类型：expense/project_cost"
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="来源记录ID"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="本次付款金额"
    )
    payment_method: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="付款方式"
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="付款时间"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_voided: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否撤销"
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
