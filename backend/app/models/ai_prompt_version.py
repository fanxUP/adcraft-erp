"""AI Prompt Version model - versioned content for prompt templates."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AIPromptVersion(Base, TimestampMixin):
    __tablename__ = "ai_prompt_versions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    template_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_prompt_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # The actual prompt content with {{variable}} placeholders
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Default values for variables: {"company_name": "默认公司"}
    variables_defaults_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    change_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # draft / active / archived
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    created_by: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("template_id", "version_number", name="uq_prompt_version_per_template"),
    )
