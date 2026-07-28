"""Phase 3: Add Prompt Center tables - templates, versions, execution logs

Revision ID: phase3_add_prompt_center
Revises: phase2_add_ai_gateway_tables
Create Date: 2026-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "phase3_add_prompt_center"
down_revision: Union[str, None] = "phase2_add_ai_gateway_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_prompt_templates ──
    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("template_code", sa.String(100), nullable=False),
        sa.Column("template_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("variables_json", JSONB, nullable=False, server_default="[]"),
        sa.Column("active_version_id", UUID, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "template_code", name="uq_prompt_template_per_tenant"),
    )

    # ── ai_prompt_versions ──
    op.create_table(
        "ai_prompt_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("template_id", UUID, nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("variables_defaults_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("change_log", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "version_number", name="uq_prompt_version_per_template"),
    )

    op.create_foreign_key(
        "fk_prompt_versions_template",
        "ai_prompt_versions", "ai_prompt_templates",
        ["template_id"], ["id"], ondelete="CASCADE",
    )

    # ── ai_prompt_execution_logs ──
    op.create_table(
        "ai_prompt_execution_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("template_id", UUID, nullable=True, index=True),
        sa.Column("version_id", UUID, nullable=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("resolved_content", sa.Text, nullable=False),
        sa.Column("variables_used_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("input_tokens", sa.BigInteger, nullable=True),
        sa.Column("output_tokens", sa.BigInteger, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("model_code", sa.String(200), nullable=True),
        sa.Column("model_role", sa.String(50), nullable=True),
        sa.Column("provider_code", sa.String(100), nullable=True),
        sa.Column("output_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_foreign_key(
        "fk_exec_logs_template",
        "ai_prompt_execution_logs", "ai_prompt_templates",
        ["template_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_exec_logs_version",
        "ai_prompt_execution_logs", "ai_prompt_versions",
        ["version_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("ai_prompt_execution_logs")
    op.drop_table("ai_prompt_versions")
    op.drop_table("ai_prompt_templates")
