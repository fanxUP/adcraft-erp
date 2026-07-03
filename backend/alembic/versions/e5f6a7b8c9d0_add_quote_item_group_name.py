"""add quote_item group_name

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('quote_items', sa.Column('group_name', sa.String(255), nullable=True, server_default=None))

def downgrade() -> None:
    op.drop_column('quote_items', 'group_name')
