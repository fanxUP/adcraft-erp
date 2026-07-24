"""为 aerial_vehicles 表添加软删除支持

Revision ID: e5f6g7h8vehicle
Revises: d5e6f7g8personnel
Create Date: 2026-07-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6g7h8vehicle'
down_revision: Union[str, None] = 'd5e6f7g8personnel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('aerial_vehicles', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('aerial_vehicles', 'deleted_at')
