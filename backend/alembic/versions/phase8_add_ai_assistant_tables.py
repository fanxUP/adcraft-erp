"""Phase 8: AI Assistant — 5 new tables

Revision ID: phase8_add_ai_assistant_tables
Revises: phase3_add_prompt_center
Create Date: 2026-07-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "phase8_add_ai_assistant_tables"
down_revision: Union[str, None] = "phase3_add_prompt_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("ai_chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("current_page", sa.String(128), nullable=True),
        sa.Column("current_business_type", sa.String(64), nullable=True),
        sa.Column("current_business_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_ai_chat_sessions_user_id", "ai_chat_sessions", ["user_id"])

    op.create_table("ai_chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("ai_chat_sessions.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, comment="user/assistant/tool/system"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_ai_chat_messages_session_id", "ai_chat_messages", ["session_id"])
    op.create_index("idx_ai_chat_messages_role", "ai_chat_messages", ["role"])

    op.create_table("ai_tool_call_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("message_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("tool_args", JSONB(), nullable=False),
        sa.Column("tool_result", JSONB(), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True, comment="level_1/level_2/level_3/level_4"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending",
                  comment="pending/running/success/failed/blocked/waiting_confirmation"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_ai_tool_call_logs_user_id", "ai_tool_call_logs", ["user_id"])
    op.create_index("idx_ai_tool_call_logs_tool_name", "ai_tool_call_logs", ["tool_name"])
    op.create_index("idx_ai_tool_call_logs_status", "ai_tool_call_logs", ["status"])

    op.create_table("ai_pending_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("ai_chat_sessions.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(128), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("tool_args", JSONB(), nullable=False),
        sa.Column("preview_data", JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="waiting_confirmation",
                  comment="waiting_confirmation/confirmed/executed/cancelled/expired/failed"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_ai_pending_actions_user_id", "ai_pending_actions", ["user_id"])
    op.create_index("idx_ai_pending_actions_status", "ai_pending_actions", ["status"])

    op.create_table("ai_operation_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(128), nullable=False),
        sa.Column("business_type", sa.String(64), nullable=True),
        sa.Column("business_id", UUID(as_uuid=True), nullable=True),
        sa.Column("before_data", JSONB(), nullable=True),
        sa.Column("after_data", JSONB(), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_ai_operation_audit_logs_user_id", "ai_operation_audit_logs", ["user_id"])
    op.create_index("idx_ai_operation_audit_logs_business", "ai_operation_audit_logs", ["business_type", "business_id"])


def downgrade() -> None:
    op.drop_table("ai_operation_audit_logs")
    op.drop_table("ai_pending_actions")
    op.drop_table("ai_tool_call_logs")
    op.drop_table("ai_chat_messages")
    op.drop_table("ai_chat_sessions")
