"""add project_costs table (clean migration)

Revision ID: 833782bd89eb
Revises: ca2b1dc1af9a
Create Date: 2026-07-08 10:09:33.433193
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '833782bd89eb'
down_revision: Union[str, None] = 'ca2b1dc1af9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('project_costs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('cost_no', sa.String(64), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cost_date', sa.DateTime(), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_project_costs_order_id')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_project_costs_customer_id')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_project_costs_created_by')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_project_costs')),
        sa.UniqueConstraint('cost_no', name=op.f('uq_project_costs_cost_no')),
    )
    op.create_index(op.f('ix_project_costs_order_id'), 'project_costs', ['order_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_costs_order_id'), table_name='project_costs')
    op.drop_table('project_costs')
