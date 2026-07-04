"""add acceptance item fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('acceptance_items', sa.Column('material_process', sa.String(255), nullable=True))
    op.add_column('acceptance_items', sa.Column('unit_price', sa.Numeric(14, 2), nullable=True))
    op.add_column('acceptance_items', sa.Column('subtotal', sa.Numeric(14, 2), nullable=True))
    op.add_column('acceptance_items', sa.Column('image_url', sa.String(500), nullable=True))

def downgrade() -> None:
    op.drop_column('acceptance_items', 'image_url')
    op.drop_column('acceptance_items', 'subtotal')
    op.drop_column('acceptance_items', 'unit_price')
    op.drop_column('acceptance_items', 'material_process')
