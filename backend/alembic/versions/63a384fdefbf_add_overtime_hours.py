"""add overtime_hours to attendance_records

Revision ID: 63a384fdefbf
Revises: 63a384fdefbd
Create Date: 2026-07-30 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '63a384fdefbf'
down_revision: Union[str, None] = '63a384fdefbd'
branch_labels: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('attendance_records', sa.Column('overtime_hours', sa.Numeric(5, 1), nullable=True))

def downgrade() -> None:
    op.drop_column('attendance_records', 'overtime_hours')
