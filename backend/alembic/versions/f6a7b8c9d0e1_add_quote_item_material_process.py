"""add quote_item material_process

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('quote_items', sa.Column('material_process', sa.String(500), nullable=True, server_default=None))

def downgrade() -> None:
    op.drop_column('quote_items', 'material_process')
