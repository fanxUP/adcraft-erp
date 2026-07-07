"""add contact_person and contact_phone to quotes and orders

Revision ID: ca2b1dc1af9a
Revises: 89cf4bec9732
Create Date: 2026-07-07 19:41:14.019100
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca2b1dc1af9a'
down_revision: Union[str, None] = '89cf4bec9732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quotes', sa.Column('contact_person', sa.String(length=64), nullable=True, comment='联系人'))
    op.add_column('quotes', sa.Column('contact_phone', sa.String(length=32), nullable=True, comment='联系电话'))
    op.add_column('orders', sa.Column('contact_person', sa.String(length=64), nullable=True, comment='联系人'))
    op.add_column('orders', sa.Column('contact_phone', sa.String(length=32), nullable=True, comment='联系电话'))


def downgrade() -> None:
    op.drop_column('quotes', 'contact_phone')
    op.drop_column('quotes', 'contact_person')
    op.drop_column('orders', 'contact_phone')
    op.drop_column('orders', 'contact_person')
