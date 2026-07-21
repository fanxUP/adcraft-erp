"""add_department_to_framework_contract_projects

Revision ID: 1be543a2e1f4
Revises: feedc0de0001
Create Date: 2026-07-22 02:25:14.344814
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1be543a2e1f4'
down_revision: Union[str, None] = 'feedc0de0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("framework_contract_projects", sa.Column("department", sa.String(255), nullable=True, comment="部门/科室"))


def downgrade() -> None:
    op.drop_column("framework_contract_projects", "department")
