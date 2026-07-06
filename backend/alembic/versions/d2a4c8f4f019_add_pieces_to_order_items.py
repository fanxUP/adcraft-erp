"""add pieces to order_items

Revision ID: d2a4c8f4f019
Revises: 15f543dcc3dc
Create Date: 2026-07-06 15:09:27.753031
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2a4c8f4f019'
down_revision: Union[str, None] = '15f543dcc3dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('order_items', sa.Column('pieces', sa.Numeric(10, 2), nullable=True, comment='件数'))
    op.execute("UPDATE order_items SET pieces = 1 WHERE pieces IS NULL")


def downgrade() -> None:
    op.drop_column('order_items', 'pieces')
