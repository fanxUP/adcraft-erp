"""AI Health Check model - records provider/model health test results."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_uuid


class AIHealthCheck(Base):
    __tablename__ = "ai_health_checks"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    provider_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True
    )
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_token_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    capability_results_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message_sanitized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
