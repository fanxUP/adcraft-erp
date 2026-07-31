"""add personnel identity/bank fields and attachments table

Revision ID: c9d0e1f2a3b4c5d6
Revises: b7c8d9e0f1a2b3c4
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c9d0e1f2a3b4c5d6'
down_revision = 'b7c8d9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── aerial_personnel 新增身份证/银行卡信息 ──
    op.add_column('aerial_personnel', sa.Column('id_card_no', sa.String(32), nullable=True))
    op.add_column('aerial_personnel', sa.Column('id_card_front_url', sa.String(500), nullable=True))
    op.add_column('aerial_personnel', sa.Column('id_card_back_url', sa.String(500), nullable=True))
    op.add_column('aerial_personnel', sa.Column('bank_card_no', sa.String(64), nullable=True))
    op.add_column('aerial_personnel', sa.Column('bank_name', sa.String(128), nullable=True))
    op.add_column('aerial_personnel', sa.Column('bank_account_name', sa.String(64), nullable=True))

    # ── aerial_personnel_attachments（人员附件，分类管理） ──
    op.create_table(
        'aerial_personnel_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('personnel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_personnel.id'), nullable=False),
        sa.Column('attachment_type', sa.String(32), server_default='other', nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(256), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('aerial_personnel_attachments')
    for col in ('bank_account_name', 'bank_name', 'bank_card_no', 'id_card_back_url', 'id_card_front_url', 'id_card_no'):
        op.drop_column('aerial_personnel', col)
