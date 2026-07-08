"""add_payee_company_name_to_project_costs

Revision ID: f05f82b3d64b
Revises: c09fe8b0f4ff
Create Date: 2026-07-08 18:32:05.705392
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f05f82b3d64b'
down_revision: Union[str, None] = 'c09fe8b0f4ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('payee_company_name', sa.String(200), nullable=True, comment='对方收款公司名称'))


def downgrade() -> None:
    op.drop_column('project_costs', 'payee_company_name')
