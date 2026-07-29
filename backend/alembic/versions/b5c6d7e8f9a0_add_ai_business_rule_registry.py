"""增加 AI 业务规则版本库和同步审计。

Revision ID: b5c6d7e8f9a0
Revises: a4c8e2f6b901
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "b5c6d7e8f9a0"
down_revision = "a4c8e2f6b901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_business_rules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("rule_key", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.String(32), nullable=False),
        sa.Column("payload_json", JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
            comment="active/superseded/retired",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "rule_key",
            "version",
            name="uq_ai_business_rule_version",
        ),
    )
    op.create_index(
        "idx_ai_business_rules_key_status",
        "ai_business_rules",
        ["rule_key", "status"],
    )

    op.create_table(
        "ai_business_rule_sync_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("catalog_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("added_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retired_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details_json", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_ai_business_rule_sync_logs_created_at",
        "ai_business_rule_sync_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_ai_business_rule_sync_logs_created_at",
        table_name="ai_business_rule_sync_logs",
    )
    op.drop_table("ai_business_rule_sync_logs")
    op.drop_index(
        "idx_ai_business_rules_key_status",
        table_name="ai_business_rules",
    )
    op.drop_table("ai_business_rules")
