"""Phase 1: Add AI provider and model tables for Model Center

Revision ID: phase1_add_ai_model_center
Revises: phase7_add_quote_geometry
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "phase1_add_ai_model_center"
down_revision: Union[str, None] = "phase7_add_quote_geometry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_providers - model service supplier configuration
    op.create_table(
        "ai_providers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("provider_code", sa.String(100), nullable=False),
        sa.Column("provider_name", sa.String(200), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False, server_default="compatible"),
        sa.Column("protocol", sa.String(50), nullable=False, server_default="openai_chat_completions"),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("full_url_mode", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("endpoint_url", sa.Text, nullable=True),
        sa.Column("auth_header", sa.String(100), nullable=False, server_default="Authorization"),
        sa.Column("auth_prefix", sa.String(50), nullable=True, server_default="Bearer"),
        sa.Column("credential_reference", sa.Text, nullable=True),
        sa.Column("custom_headers_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("proxy_config_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="2"),
        sa.Column("tls_verify", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("health_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("health_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "provider_code", name="uq_ai_providers_tenant_code"),
    )

    # ai_models - models registered under each provider
    op.create_table(
        "ai_models",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("provider_id", UUID, nullable=False),
        sa.Column("upstream_model_code", sa.String(300), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("model_role", sa.String(50), nullable=True),
        sa.Column("model_type", sa.String(50), nullable=False, server_default="chat"),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("max_output_tokens", sa.Integer, nullable=True),
        sa.Column("supports_streaming", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("supports_tools", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("supports_json_schema", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("supports_vision", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("supports_embedding", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("declared_capabilities_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("verified_capabilities_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("pricing_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("health_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("health_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider_id", "upstream_model_code", name="uq_ai_models_provider_upstream"),
    )

    # Index for faster lookups
    op.create_index("ix_ai_providers_enabled", "ai_providers", ["enabled"])
    op.create_index("ix_ai_models_provider_id", "ai_models", ["provider_id"])
    op.create_index("ix_ai_models_enabled", "ai_models", ["enabled"])


def downgrade() -> None:
    op.drop_index("ix_ai_models_enabled", table_name="ai_models")
    op.drop_index("ix_ai_models_provider_id", table_name="ai_models")
    op.drop_index("ix_ai_providers_enabled", table_name="ai_providers")
    op.drop_table("ai_models")
    op.drop_table("ai_providers")
