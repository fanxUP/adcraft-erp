"""remove standard columns from salary_rules, keep base_salary + social_insurance

Revision ID: d4e5f6a7b8c9d0e1
Revises: c3d4e5f6a7b8c9d0
Create Date: 2026-08-01 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9d0e1"
down_revision: Union[str, None] = "c3d4e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 工资规则只保留 月工资标准(base_salary)/社保金额(social_insurance)，
    # 删除 加班费率/提成比例/补贴标准/公积金/其他扣款 五个标准字段
    for col in ("overtime_rate", "commission_rate", "subsidy_standard",
                "housing_fund", "deduction_standard"):
        op.drop_column("salary_rules", col)


def downgrade() -> None:
    # 恢复标准字段（旧数据已丢，重建为空列）
    op.add_column("salary_rules", sa.Column("overtime_rate", sa.Numeric(4, 2), nullable=True))
    op.add_column("salary_rules", sa.Column("commission_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column("salary_rules", sa.Column("subsidy_standard", sa.Numeric(14, 2), nullable=True))
    op.add_column("salary_rules", sa.Column("housing_fund", sa.Numeric(14, 2), nullable=True))
    op.add_column("salary_rules", sa.Column("deduction_standard", sa.Numeric(14, 2), nullable=True))
