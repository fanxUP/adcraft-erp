"""add department to orders

Revision ID: 89cf4bec9732
Revises: d2a4c8f4f019
Create Date: 2026-07-06 16:16:50.406066
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89cf4bec9732'
down_revision: Union[str, None] = 'd2a4c8f4f019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('department', sa.String(255), nullable=True, comment='部门/科室'))


def downgrade() -> None:
    op.drop_column('orders', 'department')
