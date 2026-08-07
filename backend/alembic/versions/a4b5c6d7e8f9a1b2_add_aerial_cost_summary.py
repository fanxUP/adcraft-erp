"""add summary column to aerial_vehicle_costs

Revision ID: a4b5c6d7e8f9a1b2
Revises: e2f3a4b5c6d7e8f9
Create Date: 2026-08-07 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9a1b2'
down_revision: Union[str, None] = 'e2f3a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 高空车车辆费用摘要（一句话描述用途，区别于备注）
    op.add_column(
        'aerial_vehicle_costs',
        sa.Column('summary', sa.String(200), nullable=True, comment='费用摘要'),
    )


def downgrade() -> None:
    op.drop_column('aerial_vehicle_costs', 'summary')
