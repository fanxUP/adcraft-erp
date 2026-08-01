"""激活 旷工/全勤300/绩效300 三列（上一版迁移插入时 is_active 默认 false，未显示）

Revision ID: b2c3d4e5f6071823
Revises: a1b2c3d4e5f60718
Create Date: 2026-08-01

a1b2c3d4e5f60718 的 INSERT 未显式写 is_active，插入时列默认值恰为 false，
导致 旷工/全勤300/绩效300 三列在网页工资表缺失。此迁移将其置为 active。
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6071823'
down_revision = 'a1b2c3d4e5f60718'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "UPDATE salary_items SET is_active=true "
        "WHERE key IN ('missed_days', 'att_std', 'perf_std')"))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE salary_items SET is_active=false "
        "WHERE key IN ('missed_days', 'att_std', 'perf_std')"))
