"""add quote_id to acceptance_forms

Revision ID: a2b3c4d5e6f7
Revises: f1e2d3c4b5a6
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a2b3c4d5e6f7'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('acceptance_forms',
                  sa.Column('quote_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(None, 'acceptance_forms', 'quotes',
                          ['quote_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'acceptance_forms', type_='foreignkey')
    op.drop_column('acceptance_forms', 'quote_id')
