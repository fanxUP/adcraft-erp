"""add quote department column

Revision ID: f8a9b0c1d2e3
Revises: b2c3d4e5f6a7
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'f8a9b0c1d2e3'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('quotes', sa.Column('department', sa.String(255), nullable=True, comment='部门/科室'))

def downgrade() -> None:
    op.drop_column('quotes', 'department')
