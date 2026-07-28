"""为项目成本增加分项名称。

Revision ID: f2a9c7d1e4b6
Revises: r1s2t3u4_add_quote_mode
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a9c7d1e4b6"
down_revision = "r1s2t3u4_add_quote_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_costs", sa.Column("group_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("project_costs", "group_name")
