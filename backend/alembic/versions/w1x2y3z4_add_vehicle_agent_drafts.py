"""add vehicle agent drafts table

Revision ID: w1x2y3z4
Revises: v1v2v3v4v5v6
Create Date: 2026-07-23 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'w1x2y3z4'
down_revision: Union[str, None] = 'v1v2v3v4v5v6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vehicle_agent_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('intent', sa.String(64), nullable=False),
        sa.Column('confidence', sa.Numeric(4, 2), server_default='0', nullable=False),
        sa.Column('risk_level', sa.String(16), server_default='medium', nullable=False),
        sa.Column('status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('platform', sa.String(32), server_default='manual', nullable=False),
        sa.Column('conversation_id', sa.String(128), nullable=True),
        sa.Column('message_id', sa.String(128), nullable=True),
        sa.Column('sender_name', sa.String(64), nullable=True),
        sa.Column('sender_id', sa.String(128), nullable=True),
        sa.Column('original_content', sa.Text, nullable=False),
        sa.Column('extracted_data', postgresql.JSONB, nullable=True),
        sa.Column('suggested_action', sa.String(64), nullable=True),
        sa.Column('requires_confirmation', sa.Boolean, server_default='true', nullable=False),
        sa.Column('requires_finance_review', sa.Boolean, server_default='false', nullable=False),
        sa.Column('confirmed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('confirmed_at', sa.DateTime, nullable=True),
        sa.Column('reject_reason', sa.Text, nullable=True),
        sa.Column('created_draft_id', sa.String(64), nullable=True),
        sa.Column('created_draft_type', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_agent_drafts_status', 'vehicle_agent_drafts', ['status'])
    op.create_index('ix_vehicle_agent_drafts_intent', 'vehicle_agent_drafts', ['intent'])
    op.create_index('ix_vehicle_agent_drafts_platform', 'vehicle_agent_drafts', ['platform'])


def downgrade() -> None:
    op.drop_table('vehicle_agent_drafts')
