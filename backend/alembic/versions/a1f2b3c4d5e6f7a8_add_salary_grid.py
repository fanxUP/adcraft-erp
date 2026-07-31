"""工资网格：指标定义 salary_items + 单元格值 salary_grid_values

Revision ID: a1f2b3c4d5e6f7a8
Revises: e1f2a3b4c5d6e7f8
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a1f2b3c4d5e6f7a8'
down_revision = 'e1f2a3b4c5d6e7f8'
branch_labels = None
depends_on = None

# 预置内置指标（公式为 Python 风格表达式，见 app/services/salary_formula.py）
SEED_ITEMS = [
    ("basic", "基本工资", "base", 1),
    ("ot_hours", "加班工时", "ot_hours", 2),
    ("overtime_pay", "加班费", "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)", 3),
    ("bonus", "绩效", "bonus_std", 4),
    ("subsidy", "伙食补助", "subsidy_std", 5),
    ("att_bonus", "全勤奖", "att_bonus if (missed_days == 0 and absent_days == 0) else 0", 6),
    ("social", "社保", "social", 7),
    ("housing", "公积金", "housing", 8),
    ("deduction", "扣款合计", "social + housing + ded_std", 9),
    ("gross", "应发工资", "basic + overtime_pay + bonus + subsidy + att_bonus", 10),
    ("net", "实发工资", "max(0, gross - deduction)", 11),
]


def upgrade() -> None:
    op.create_table(
        "salary_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("formula", sa.Text(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )
    op.create_table(
        "salary_grid_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("item_key", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(14, 2), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="computed"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("month", "employee_id", "item_key", name="uq_salary_grid_month_emp_item"),
    )

    for key, label, formula, order in SEED_ITEMS:
        op.execute(
            sa.text(
                "INSERT INTO salary_items (id, key, label, formula, sort_order, is_builtin) "
                "VALUES (gen_random_uuid(), :key, :label, :formula, :order, true)"
            ).bindparams(key=key, label=label, formula=formula, order=order)
        )


def downgrade() -> None:
    op.drop_table("salary_grid_values")
    op.drop_table("salary_items")
