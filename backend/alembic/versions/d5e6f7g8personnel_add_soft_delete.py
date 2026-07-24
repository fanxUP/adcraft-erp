"""add soft-delete (deleted_at) to aerial_personnel

Revision ID: d5e6f7g8personnel
Revises: c3d4e5f6personnel
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7g8personnel'
down_revision: Union[str, None] = 'c3d4e5f6personnel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('aerial_personnel', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('aerial_personnel', 'deleted_at')
