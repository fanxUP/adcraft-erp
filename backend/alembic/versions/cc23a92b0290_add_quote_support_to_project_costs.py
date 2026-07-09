"""add_quote_support_to_project_costs

Revision ID: cc23a92b0290
Revises: f05f82b3d64b
Create Date: 2026-07-08 18:32:05.705392
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cc23a92b0290'
down_revision: Union[str, None] = 'f05f82b3d64b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('source_type', sa.String(16), nullable=False, server_default='order', comment='来源类型：order/quote'))
    op.add_column('project_costs', sa.Column('quote_id', sa.UUID(), nullable=True))
    op.alter_column('project_costs', 'order_id', existing_type=sa.UUID(), nullable=True)
    op.create_foreign_key('fk_project_costs_quote_id', 'project_costs', 'quotes', ['quote_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_project_costs_quote_id', 'project_costs', type_='foreignkey')
    op.alter_column('project_costs', 'order_id', existing_type=sa.UUID(), nullable=False)
    op.drop_column('project_costs', 'quote_id')
    op.drop_column('project_costs', 'source_type')
