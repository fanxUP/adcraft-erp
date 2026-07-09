"""add quantity/unit/unit_price to project_costs

Revision ID: cc23a92b0293
Revises: 8309d8ebb025
Create Date: 2026-07-09 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "cc23a92b0293"
down_revision: Union[str, None] = "8309d8ebb025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('quantity', sa.Numeric(14, 2), nullable=True, comment='数量'))
    op.add_column('project_costs', sa.Column('unit', sa.String(32), nullable=True, comment='单位'))
    op.add_column('project_costs', sa.Column('unit_price', sa.Numeric(14, 2), nullable=True, comment='单价'))


def downgrade() -> None:
    op.drop_column('project_costs', 'unit_price')
    op.drop_column('project_costs', 'unit')
    op.drop_column('project_costs', 'quantity')
