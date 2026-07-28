"""AI Task Route model - maps task types to provider/model configurations."""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AITaskRoute(Base, TimestampMixin):
    __tablename__ = "ai_task_routes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    task_code: Mapped[str] = mapped_column(String(150), nullable=False)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Primary model reference
    primary_provider_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    primary_model_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Fallback chain — ordered list of {provider_id, model_role} objects
    fallback_chain_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list)

    # Required capabilities the model must support
    required_capabilities_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Execution parameters
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)

    # Budget and data policy
    budget_policy_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    data_policy_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Circuit breaker settings
    circuit_breaker_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    # Default: {"failure_threshold": 5, "rolling_window_seconds": 120, "open_duration_seconds": 60, "half_open_probe_count": 2}

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_by: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("tenant_id", "task_code", name="uq_task_route_per_tenant"),
    )
