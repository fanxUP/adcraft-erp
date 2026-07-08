"""add_order_item_id_to_project_costs

Revision ID: 85ddbdc2b996
Revises: 833782bd89eb
Create Date: 2026-07-08 18:32:05.705392
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85ddbdc2b996'
down_revision: Union[str, None] = '833782bd89eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_costs', sa.Column('order_item_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_project_costs_order_item_id', 'project_costs', 'order_items', ['order_item_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_project_costs_order_item_id', 'project_costs', type_='foreignkey')
    op.drop_column('project_costs', 'order_item_id')
