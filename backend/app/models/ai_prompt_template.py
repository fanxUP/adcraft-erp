"""AI Prompt Template model - reusable prompt templates with versioning."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, gen_uuid


class AIPromptTemplate(Base, TimestampMixin):
    __tablename__ = "ai_prompt_templates"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Variable definitions: [{"name": "company_name", "label": "公司名称", "default": "", "required": true}]
    variables_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Current active version ID (FK to ai_prompt_versions)
    active_version_id: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_by: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("tenant_id", "template_code", name="uq_prompt_template_per_tenant"),
    )
