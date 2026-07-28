"""AI Prompt Execution Log - logs test executions of prompts."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_uuid


class AIPromptExecutionLog(Base):
    __tablename__ = "ai_prompt_execution_logs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    template_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)

    # Resolved prompt after variable substitution
    resolved_content: Mapped[str] = mapped_column(Text, nullable=False)
    variables_used_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # AI execution results
    input_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_code: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    model_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Response
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
