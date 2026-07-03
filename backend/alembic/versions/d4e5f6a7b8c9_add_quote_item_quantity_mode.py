"""add quote_item quantity_mode

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('quote_items', sa.Column('quantity_mode', sa.String(16), server_default='piece', nullable=False))

def downgrade() -> None:
    op.drop_column('quote_items', 'quantity_mode')
