"""AI Usage Daily model - aggregates daily token usage and cost."""
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, Date, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AIUsageDaily(Base, TimestampMixin):
    __tablename__ = "ai_usage_daily"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    provider_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    model_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    task_code: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Aggregated counts
    request_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Token totals
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Cost
    estimated_cost: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=0)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Performance
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Numeric(18, 3), nullable=True)

    __table_args__ = (
        __import__("sqlalchemy").Index("ix_usage_daily_lookup", "tenant_id", "usage_date", "task_code"),
    )
