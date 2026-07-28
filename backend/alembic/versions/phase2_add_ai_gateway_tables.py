"""Phase 2: Add AI Gateway tables for routing, logging, usage, and health checks

Revision ID: phase2_add_ai_gateway_tables
Revises: phase1_add_ai_model_center
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "phase2_add_ai_gateway_tables"
down_revision: Union[str, None] = "phase1_add_ai_model_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_task_routes ──
    op.create_table(
        "ai_task_routes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("task_code", sa.String(150), nullable=False),
        sa.Column("task_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),

        # Primary model
        sa.Column("primary_provider_id", UUID, nullable=True),
        sa.Column("primary_model_role", sa.String(50), nullable=True),

        # Fallback chain: JSON array of {provider_id, model_role}
        sa.Column("fallback_chain_json", JSONB, nullable=True, server_default="[]"),
        sa.Column("required_capabilities_json", JSONB, nullable=True, server_default="{}"),

        # Execution params
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("max_output_tokens", sa.Integer, nullable=True),
        sa.Column("temperature", sa.Numeric(4, 3), nullable=True),

        # Budget & data policy
        sa.Column("budget_policy_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("data_policy_json", JSONB, nullable=True, server_default="{}"),

        # Circuit breaker config
        sa.Column("circuit_breaker_json", JSONB, nullable=True, server_default="{}"),

        # Status
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "task_code", name="uq_task_route_per_tenant"),
    )

    # Foreign keys for ai_task_routes
    op.create_foreign_key(
        "fk_task_routes_provider", "ai_task_routes", "ai_providers",
        ["primary_provider_id"], ["id"], ondelete="SET NULL",
    )

    # ── ai_requests ──
    op.create_table(
        "ai_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("request_id", sa.String(100), nullable=False, unique=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("user_id", UUID, nullable=True, index=True),
        sa.Column("department_id", UUID, nullable=True),

        sa.Column("task_code", sa.String(150), nullable=False, index=True),

        # Provider/model used
        sa.Column("provider_id", UUID, nullable=True),
        sa.Column("model_id", UUID, nullable=True),
        sa.Column("model_code", sa.String(200), nullable=True),

        # Business context
        sa.Column("business_object_type", sa.String(100), nullable=True),
        sa.Column("business_object_id", UUID, nullable=True),

        # Content summary
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),

        # Status & execution
        sa.Column("status", sa.String(30), nullable=False, server_default="pending", index=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer, nullable=False, server_default="0"),

        # Performance
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer, nullable=True),

        # Token usage
        sa.Column("input_tokens", sa.BigInteger, nullable=True),
        sa.Column("cached_input_tokens", sa.BigInteger, nullable=True),
        sa.Column("output_tokens", sa.BigInteger, nullable=True),

        # Cost
        sa.Column("estimated_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),

        # Error
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message_sanitized", sa.Text, nullable=True),

        # Timing
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_requests_provider", "ai_requests", "ai_providers",
        ["provider_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_requests_model", "ai_requests", "ai_models",
        ["model_id"], ["id"], ondelete="SET NULL",
    )

    # ── ai_usage_daily ──
    op.create_table(
        "ai_usage_daily",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("usage_date", sa.Date, nullable=False, index=True),
        sa.Column("provider_id", UUID, nullable=True),
        sa.Column("model_id", UUID, nullable=True),
        sa.Column("task_code", sa.String(150), nullable=True),

        sa.Column("request_count", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("success_count", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.BigInteger, nullable=False, server_default="0"),

        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("cached_input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),

        sa.Column("estimated_cost", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("avg_latency_ms", sa.Numeric(18, 3), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_usage_daily_lookup", "ai_usage_daily",
        ["tenant_id", "usage_date", "task_code"],
    )

    # ── ai_health_checks ──
    op.create_table(
        "ai_health_checks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("provider_id", UUID, nullable=False, index=True),
        sa.Column("model_id", UUID, nullable=True),
        sa.Column("check_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer, nullable=True),
        sa.Column("capability_results_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message_sanitized", sa.Text, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_foreign_key(
        "fk_health_checks_provider", "ai_health_checks", "ai_providers",
        ["provider_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_health_checks_model", "ai_health_checks", "ai_models",
        ["model_id"], ["id"], ondelete="SET NULL",
    )

    # ── Add updated_at trigger for ai_task_routes ──
    # (Handled by SQLAlchemy's onupdate in the model)


def downgrade() -> None:
    op.drop_table("ai_health_checks")
    op.drop_table("ai_usage_daily")
    op.drop_index("ix_usage_daily_lookup", table_name="ai_usage_daily")
    op.drop_table("ai_requests")
    op.drop_table("ai_task_routes")
