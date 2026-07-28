"""AI Provider model - suppliers of AI model APIs."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AIProvider(Base, TimestampMixin):
    __tablename__ = "ai_providers"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=gen_uuid)
    tenant_id: Mapped[UUID] = mapped_column(PUUID, nullable=False)
    provider_code: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False, default="compatible")
    protocol: Mapped[str] = mapped_column(String(50), nullable=False, default="openai_chat_completions")
    base_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_url_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    endpoint_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auth_header: Mapped[str] = mapped_column(String(100), nullable=False, default="Authorization")
    auth_prefix: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="Bearer")
    credential_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_headers_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    proxy_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    tls_verify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    health_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    health_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), nullable=True)
    last_health_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(PUUID, nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PUUID, nullable=True)

    __table_args__ = ({"extend_existing": True},)
