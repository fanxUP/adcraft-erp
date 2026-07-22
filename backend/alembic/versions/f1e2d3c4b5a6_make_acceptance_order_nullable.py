"""make acceptance_form order_id nullable

Revision ID: f1e2d3c4b5a6
Revises: 1be543a2e1f4
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f1e2d3c4b5a6'
down_revision = '1be543a2e1f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('acceptance_forms', 'order_id',
                    existing_type=UUID(as_uuid=True),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('acceptance_forms', 'order_id',
                    existing_type=UUID(as_uuid=True),
                    nullable=False)
