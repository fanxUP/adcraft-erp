"""add quote_date to business_documents

Revision ID: b0c1d2e3f4a5
Revises: a4b5c6d7e8f9a1b2
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'b0c1d2e3f4a5'
down_revision = 'a4b5c6d7e8f9a1b2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('business_documents', sa.Column('quote_date', sa.Date(), nullable=True, comment='报价日期（手动可选）'))

def downgrade() -> None:
    op.drop_column('business_documents', 'quote_date')
