"""add attachment fields to contracts

Revision ID: fa0b1c2d3e4f
Revises: f8a9b0c1d2e3
Create Date: 2026-07-17 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa0b1c2d3e4f'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contracts', sa.Column('attachment_path', sa.String(length=500), nullable=True, comment='合同原件存储路径'))
    op.add_column('contracts', sa.Column('attachment_name', sa.String(length=255), nullable=True, comment='合同原件文件名'))


def downgrade() -> None:
    op.drop_column('contracts', 'attachment_name')
    op.drop_column('contracts', 'attachment_path')
