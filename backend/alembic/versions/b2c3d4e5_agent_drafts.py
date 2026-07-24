"""add aerial_agent_drafts table

Revision ID: b2c3d4e5agent
Revises: a1b2c3d4aerial
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "b2c3d4e5agent"
down_revision = "a1b2c3d4aerial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "aerial_agent_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False, comment="来源平台"),
        sa.Column("conversation_id", sa.String(128), nullable=True, comment="会话ID"),
        sa.Column("message_id", sa.String(128), nullable=True, comment="消息ID"),
        sa.Column("sender_id", sa.String(128), nullable=True, comment="发送人ID"),
        sa.Column("sender_name", sa.String(64), nullable=True, comment="发送人名称"),
        sa.Column("raw_message", sa.Text, nullable=False, comment="原始消息"),
        sa.Column("intent", sa.String(64), nullable=False, comment="识别意图"),
        sa.Column("confidence", sa.Float, server_default="0", nullable=False, comment="置信度"),
        sa.Column("risk_level", sa.String(16), server_default="low", nullable=False, comment="风险等级"),
        sa.Column("extracted_json", sa.Text, nullable=True, comment="提取数据JSON"),
        sa.Column("suggested_action", sa.String(64), nullable=True, comment="建议动作"),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False, comment="草稿状态"),
        sa.Column("confirmed_by", UUID(as_uuid=True), nullable=True, comment="确认人"),
        sa.Column("confirmed_at", sa.DateTime, nullable=True, comment="确认时间"),
        sa.Column("reject_reason", sa.Text, nullable=True, comment="拒绝原因"),
        sa.Column("created_ledger_id", UUID(as_uuid=True), sa.ForeignKey("aerial_daily_ledgers.id"), nullable=True, comment="生成的台账ID"),
        sa.Column("created_expense_id", UUID(as_uuid=True), sa.ForeignKey("aerial_personnel_expenses.id"), nullable=True, comment="生成的垫付ID"),
        sa.Column("created_cost_id", UUID(as_uuid=True), sa.ForeignKey("aerial_vehicle_costs.id"), nullable=True, comment="生成的车辆费用ID"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_aerial_drafts_status", "aerial_agent_drafts", ["status"])
    op.create_index("ix_aerial_drafts_platform", "aerial_agent_drafts", ["platform"])
    op.create_index("ix_aerial_drafts_sender", "aerial_agent_drafts", ["sender_id"])


def downgrade():
    op.drop_table("aerial_agent_drafts")
