"""add gender/ethnicity to aerial_personnel and employees

Revision ID: d5e6f7a8b9c0d1e2
Revises: c9d0e1f2a3b4c5d6
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0d1e2'
down_revision = 'c9d0e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 高空车人员：性别(编码 male/female，与员工模块一致) + 族别(存中文值) ──
    op.add_column('aerial_personnel', sa.Column('gender', sa.String(8), nullable=True, comment='性别: male/female'))
    op.add_column('aerial_personnel', sa.Column('ethnicity', sa.String(32), nullable=True, comment='族别'))
    # ── 员工：族别 ──
    op.add_column('employees', sa.Column('ethnicity', sa.String(32), nullable=True, comment='族别'))


def downgrade() -> None:
    op.drop_column('employees', 'ethnicity')
    op.drop_column('aerial_personnel', 'ethnicity')
    op.drop_column('aerial_personnel', 'gender')
