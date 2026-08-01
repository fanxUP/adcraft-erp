"""remove bonus fields from salary_rules, drop std columns, hide missed_days

Revision ID: c3d4e5f6a7b8c9d0
Revises: a9b0c1d2e3f4a5b6
Create Date: 2026-08-01 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8c9d0"
down_revision: Union[str, None] = "a9b0c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 工资规则去掉 全勤奖/奖金标准 两字段
    op.drop_column("salary_rules", "bonus_standard")
    op.drop_column("salary_rules", "attendance_bonus")
    # 删除 全勤300/绩效300 指标列（含历史网格值；内置列无法从 UI 删除）
    for key in ("att_std", "perf_std"):
        op.execute(sa.text("DELETE FROM salary_grid_values WHERE item_key=:key").bindparams(key=key))
        op.execute(sa.text("DELETE FROM salary_items WHERE key=:key").bindparams(key=key))
    # 旷工默认关闭（历史数据保留，指标设置里可重新启用）
    op.execute(sa.text("UPDATE salary_items SET is_active=false WHERE key='missed_days'"))


def downgrade() -> None:
    # 恢复规则字段（旧数据已丢，重建为空列）
    op.add_column("salary_rules", sa.Column("bonus_standard", sa.Numeric(14, 2), nullable=True))
    op.add_column("salary_rules", sa.Column("attendance_bonus", sa.Numeric(14, 2), nullable=True))
    # 恢复指标列（历史网格值已无法找回，仅重建列）
    INSERT_ITEMS = [
        ("att_std", "全勤300", None, None, 2, "att_bonus", False),
        ("perf_std", "绩效300", None, None, 3, "bonus_std", False),
    ]
    for key, label, g1, g2, order, formula, manual in INSERT_ITEMS:
        op.execute(
            sa.text(
                "INSERT INTO salary_items (id, key, label, formula, sort_order, "
                "is_builtin, is_manual, group1, group2) "
                "SELECT gen_random_uuid(), :key, :label, :formula, :order, true, :manual, :g1, :g2 "
                "WHERE NOT EXISTS (SELECT 1 FROM salary_items WHERE key=:key)"
            ).bindparams(key=key, label=label, formula=formula, order=order,
                         manual=manual, g1=g1, g2=g2)
        )
    op.execute(sa.text("UPDATE salary_items SET is_active=true WHERE key='missed_days'"))
