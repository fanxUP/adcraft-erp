"""add_payment_method_and_debt_fields_to_project_costs

Revision ID: c09fe8b0f4ff
Revises: 85ddbdc2b996
Create Date: 2026-07-08 18:32:05.705392
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c09fe8b0f4ff'
down_revision: Union[str, None] = '85ddbdc2b996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('payment_method', sa.String(32), nullable=True, comment='付款方式'))
    op.add_column('project_costs', sa.Column('debt_amount', sa.Numeric(14, 2), nullable=True, default=0, comment='欠款金额'))
    op.add_column('project_costs', sa.Column('is_debt', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='是否为欠款'))
    op.add_column('project_costs', sa.Column('is_settled', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='欠款是否已结清'))
    op.add_column('project_costs', sa.Column('settled_at', sa.DateTime(), nullable=True, comment='欠款结清时间'))


def downgrade() -> None:
    op.drop_column('project_costs', 'settled_at')
    op.drop_column('project_costs', 'is_settled')
    op.drop_column('project_costs', 'is_debt')
    op.drop_column('project_costs', 'debt_amount')
    op.drop_column('project_costs', 'payment_method')
