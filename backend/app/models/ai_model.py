"""AIModel model - models registered under each provider."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AIModel(Base, TimestampMixin):
    __tablename__ = "ai_models"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=gen_uuid)
    tenant_id: Mapped[UUID] = mapped_column(PUUID, nullable=False)
    provider_id: Mapped[UUID] = mapped_column(PUUID, ForeignKey("ai_providers.id"), nullable=False)
    upstream_model_code: Mapped[str] = mapped_column(String(300), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_json_schema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_embedding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    declared_capabilities_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    verified_capabilities_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    pricing_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    health_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    health_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = ({"extend_existing": True},)
