"""add pieces to quote_items

Revision ID: 15f543dcc3dc
Revises: f8a9b0c1d2e3
Create Date: 2026-07-06 14:28:08.095234
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15f543dcc3dc'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quote_items', sa.Column('pieces', sa.Numeric(10, 2), nullable=True, comment='件数'))
    op.execute("UPDATE quote_items SET pieces = 1 WHERE pieces IS NULL")


def downgrade() -> None:
    op.drop_column('quote_items', 'pieces')
