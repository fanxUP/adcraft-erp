"""add_summary_to_project_costs

Revision ID: cc23a92b0291
Revises: cc23a92b0290
Create Date: 2026-07-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cc23a92b0291'
down_revision: Union[str, None] = 'cc23a92b0290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('summary', sa.Text(), nullable=True, comment='成本摘要'))


def downgrade() -> None:
    op.drop_column('project_costs', 'summary')
