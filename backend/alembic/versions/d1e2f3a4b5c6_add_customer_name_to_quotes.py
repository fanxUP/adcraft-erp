"""add customer_name to quotes

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add customer_name column to quotes table
    op.add_column('quotes', sa.Column('customer_name', sa.String(255), nullable=True))
    # Make customer_id nullable (quotes can exist without a linked customer)
    op.alter_column('quotes', 'customer_id', existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column('quotes', 'customer_id', existing_type=sa.UUID(), nullable=False)
    op.drop_column('quotes', 'customer_name')
