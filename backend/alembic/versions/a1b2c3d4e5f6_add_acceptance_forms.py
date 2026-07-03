"""add acceptance forms

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a1b2c3d4e5f6'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'acceptance_forms',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('acceptance_no', sa.String(64), unique=True, nullable=False),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('status', sa.String(64), nullable=False, server_default='draft'),
        sa.Column('accepted_at', sa.DateTime, nullable=True),
        sa.Column('accepted_by', sa.String(128), nullable=True),
        sa.Column('our_acceptor_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('reject_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'acceptance_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('acceptance_id', UUID(as_uuid=True), sa.ForeignKey('acceptance_forms.id'), nullable=False),
        sa.Column('order_item_id', UUID(as_uuid=True), sa.ForeignKey('order_items.id'), nullable=True),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('specification', sa.String(500), nullable=True),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=True),
        sa.Column('unit', sa.String(32), nullable=True),
        sa.Column('item_status', sa.String(64), nullable=False, server_default='pending'),
        sa.Column('remark', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'acceptance_attachments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('acceptance_id', UUID(as_uuid=True), sa.ForeignKey('acceptance_forms.id'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('filepath', sa.String(500), nullable=False),
        sa.Column('filesize', sa.Integer, nullable=True),
        sa.Column('upload_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table('acceptance_attachments')
    op.drop_table('acceptance_items')
    op.drop_table('acceptance_forms')
