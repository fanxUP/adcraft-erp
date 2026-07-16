"""add specification to project costs

Revision ID: d3030d853061
Revises: c3030d853060
Create Date: 2026-07-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3030d853061'
down_revision: Union[str, None] = 'c3030d853060'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('specification', sa.String(length=255), nullable=True, comment='规格尺寸'))


def downgrade() -> None:
    op.drop_column('project_costs', 'specification')
