"""AI Request model - logs every AI API call with usage and status."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_uuid


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True, index=True)
    department_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    task_code: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    provider_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    model_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True
    )
    model_code: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Business context
    business_object_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_object_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    # Request content (truncated/summarized)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status & execution
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Performance
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_token_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Token usage
    input_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    cached_input_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Cost
    estimated_cost: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Error
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message_sanitized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
