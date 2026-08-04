"""remove aerial ledger status/audit feature

Revision ID: e9f0a1b2c3d4e5f6
Revises: d8c17b6531644a69
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e9f0a1b2c3d4e5f6'
down_revision = 'd8c17b6531644a69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 台账状态/审核状态/审核人/作废信息 字段与索引
    op.drop_index('ix_aerial_ledger_status', table_name='aerial_daily_ledgers')
    op.drop_column('aerial_daily_ledgers', 'status')
    op.drop_column('aerial_daily_ledgers', 'audit_status')
    op.drop_column('aerial_daily_ledgers', 'reviewed_by')
    op.drop_column('aerial_daily_ledgers', 'reviewed_at')
    op.drop_column('aerial_daily_ledgers', 'voided_by')
    op.drop_column('aerial_daily_ledgers', 'voided_at')
    op.drop_column('aerial_daily_ledgers', 'void_reason')
    # 台账审计日志表
    op.drop_table('aerial_ledger_audit_logs')


def downgrade() -> None:
    op.create_table(
        'aerial_ledger_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=True),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('source', sa.String(32), server_default='erp', nullable=False),
        sa.Column('target_type', sa.String(64), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('before_json', sa.Text, nullable=True),
        sa.Column('after_json', sa.Text, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.add_column('aerial_daily_ledgers', sa.Column('status', sa.String(32), server_default='draft', nullable=False))
    op.add_column('aerial_daily_ledgers', sa.Column('audit_status', sa.String(32), server_default='pending', nullable=False))
    op.add_column('aerial_daily_ledgers', sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('aerial_daily_ledgers', sa.Column('reviewed_at', sa.DateTime, nullable=True))
    op.add_column('aerial_daily_ledgers', sa.Column('voided_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('aerial_daily_ledgers', sa.Column('voided_at', sa.DateTime, nullable=True))
    op.add_column('aerial_daily_ledgers', sa.Column('void_reason', sa.Text, nullable=True))
    op.create_index('ix_aerial_ledger_status', 'aerial_daily_ledgers', ['status'])
