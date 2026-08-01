"""三层分组表头：salary_items 加 group1/group2；指标改为传统工资表布局

Revision ID: f0e1d2c3b4a59687
Revises: 3c4d5e6f7a8b9c0d
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f0e1d2c3b4a59687'
down_revision = '3c4d5e6f7a8b9c0d'
branch_labels = None
depends_on = None

# 已有内置项重排：key -> (label, group1, group2, sort_order, formula)
UPDATE_ITEMS = [
    ("basic", "基本工资", "应发金额", "基本部分", 2, "base"),
    ("ot_hours", "加班小时", "应发金额", "基本部分", 3, "ot_hours"),
    ("overtime_pay", "加班费", "应发金额", "基本部分", 4,
     "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5)"),
    ("att_bonus", "全勤/话费补助", "应发金额", "基本部分", 5,
     "att_bonus if (missed_days == 0 and absent_days == 0) else 0"),
    ("subsidy", "伙食补助", "应发金额", "基本部分", 6, "subsidy_std"),
    ("bonus", "绩效工资", "应发金额", "绩效部分", 9, "bonus_std"),
    ("social", "社保扣款", "应扣金额", None, 15, "social"),
    ("deduction", "应扣合计", "应扣金额", None, 17, "social + other_deduction"),
    ("gross", "应发合计", "应发金额", "未出勤", 14,
     "base_total + bonus_total - absent_deduction"),
    ("net", "实发工资", None, None, 18, "max(0, gross - deduction)"),
]

# 新增内置项：key, label, group1, group2, sort_order, formula, is_manual
INSERT_ITEMS = [
    ("attend_days", "出勤天数", "应发金额", "基本部分", 1, "attend_days", False),
    ("other_base", "其他", "应发金额", "基本部分", 7, "", True),
    ("base_total", "合计", "应发金额", "基本部分", 8,
     "basic + overtime_pay + att_bonus + subsidy + other_base", False),
    ("other_bonus", "其他", "应发金额", "绩效部分", 10, "", True),
    ("bonus_total", "合计", "应发金额", "绩效部分", 11, "bonus + other_bonus", False),
    ("absent_days", "未出勤天数", "应发金额", "未出勤", 12, "absent_days", False),
    ("absent_deduction", "未出勤扣减", "应发金额", "未出勤", 13,
     "absent_days * (base / 21.75)", False),
    ("other_deduction", "其他", "应扣金额", None, 16, "", True),
    ("social_company", "社保", "代缴部分", None, 19, "", True),
    ("other_company", "其他", "代缴部分", None, 20, "", True),
    ("last_net", "上月实发工资", None, None, 22, "", True),
]


def upgrade() -> None:
    op.add_column("salary_items", sa.Column("group1", sa.String(64), nullable=True))
    op.add_column("salary_items", sa.Column("group2", sa.String(64), nullable=True))

    for key, label, g1, g2, order, formula in UPDATE_ITEMS:
        op.execute(
            sa.text(
                "UPDATE salary_items SET label=:label, group1=:g1, group2=:g2, "
                "sort_order=:order, formula=:formula, is_manual=false WHERE key=:key"
            ).bindparams(key=key, label=label, g1=g1, g2=g2, order=order, formula=formula)
        )

    # 公积金列不再参与标准表头，停用（保留行可恢复）
    op.execute(
        sa.text("UPDATE salary_items SET is_active=false, group1=NULL, group2=NULL "
                "WHERE key='housing'")
    )

    for key, label, g1, g2, order, formula, manual in INSERT_ITEMS:
        op.execute(
            sa.text(
                "INSERT INTO salary_items (id, key, label, formula, sort_order, "
                "is_builtin, is_manual, group1, group2) "
                "VALUES (gen_random_uuid(), :key, :label, :formula, :order, true, :manual, :g1, :g2)"
            ).bindparams(key=key, label=label, formula=formula, order=order,
                         manual=manual, g1=g1, g2=g2)
        )


def downgrade() -> None:
    op.drop_column("salary_items", "group2")
    op.drop_column("salary_items", "group1")
