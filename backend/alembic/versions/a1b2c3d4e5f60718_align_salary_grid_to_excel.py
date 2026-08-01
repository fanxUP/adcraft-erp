"""工资表字段对齐原版 Excel：旷工/全勤300/绩效300/月工资标准 独立列，考勤栏/代缴费用 二级组

Revision ID: a1b2c3d4e5f60718
Revises: f0e1d2c3b4a59687
Create Date: 2026-08-01

- 全勤奖 item 改名 att_bonus -> att_award（避免与规则变量 att_bonus 撞名，
  否则「全勤300」公式依赖会被路由到全勤奖 item）。旧月网格值 key 一并重映射。
- 月工资标准(basic) 移出基本部分，成为独立列。
- 新增 旷工(missed_days)/全勤300(att_std)/绩效300(perf_std) 三个独立列。
- absent_days/absent_deduction 二级组 未出勤 -> 考勤栏；gross 二级组置空(独立 rowspan2)。
- social/other_deduction 二级组 -> 代缴费用；deduction 二级组置空。
- 停用原表没有的 attend_days/social_company/other_company（数据保留可恢复）。
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f60718'
down_revision = 'f0e1d2c3b4a59687'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. 全勤奖 item 改名（先改网格值，再改指标定义）──
    op.execute(sa.text(
        "UPDATE salary_grid_values SET item_key='att_award' WHERE item_key='att_bonus'"))
    op.execute(sa.text(
        "UPDATE salary_items SET key='att_award', label='全勤奖', "
        "group1='应发金额', group2='基本部分', sort_order=7, is_manual=false "
        "WHERE key='att_bonus'"))

    # ── 2. 重排/改名/改组现有项（对齐原版 Excel 列序）──
    op.execute(sa.text(
        "UPDATE salary_items SET label='月工资标准', group1=NULL, group2=NULL, "
        "sort_order=4, formula='base', is_manual=false WHERE key='basic'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=5 WHERE key='ot_hours'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=6 WHERE key='overtime_pay'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=8 WHERE key='subsidy'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=9 WHERE key='other_base'"))
    op.execute(sa.text(
        "UPDATE salary_items SET sort_order=10, "
        "formula='basic + overtime_pay + att_award + subsidy + other_base' "
        "WHERE key='base_total'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=11 WHERE key='bonus'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=12 WHERE key='other_bonus'"))
    op.execute(sa.text("UPDATE salary_items SET sort_order=13 WHERE key='bonus_total'"))
    op.execute(sa.text(
        "UPDATE salary_items SET label='未出勤天数', group2='考勤栏', "
        "sort_order=14, formula='absent_days', is_manual=false WHERE key='absent_days'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group2='考勤栏', sort_order=15, "
        "formula='absent_days * (base / 21.75)' WHERE key='absent_deduction'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group2=NULL, sort_order=16, "
        "formula='base_total + bonus_total - absent_deduction' WHERE key='gross'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group2='代缴费用', sort_order=17, "
        "formula='social', is_manual=false WHERE key='social'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group2='代缴费用', sort_order=18, "
        "is_manual=true WHERE key='other_deduction'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group2=NULL, sort_order=19, "
        "formula='social + other_deduction' WHERE key='deduction'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group1=NULL, group2=NULL, sort_order=20, "
        "formula='max(0, gross - deduction)' WHERE key='net'"))
    op.execute(sa.text(
        "UPDATE salary_items SET group1=NULL, group2=NULL, sort_order=22, "
        "is_manual=true WHERE key='last_net'"))

    # ── 3. 隐藏原表没有的列（数据保留，指标设置里可恢复）──
    for key in ("attend_days", "social_company", "other_company"):
        op.execute(sa.text("UPDATE salary_items SET is_active=false WHERE key=:key")
                   .bindparams(key=key))

    # ── 4. 新增：旷工 / 全勤300 / 绩效300（独立列）──
    INSERT_ITEMS = [
        ("missed_days", "旷工", None, None, 1, "missed_days", False),
        ("att_std", "全勤300", None, None, 2, "att_bonus", False),
        ("perf_std", "绩效300", None, None, 3, "bonus_std", False),
    ]
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
    # 反向（尽量）：删新增项、恢复 key 名、恢复基础 label/sort，其余分组不逐项还原
    for key in ("missed_days", "att_std", "perf_std"):
        op.execute(sa.text("DELETE FROM salary_grid_values WHERE item_key=:key")
                   .bindparams(key=key))
        op.execute(sa.text("DELETE FROM salary_items WHERE key=:key").bindparams(key=key))
    op.execute(sa.text(
        "UPDATE salary_grid_values SET item_key='att_bonus' WHERE item_key='att_award'"))
    op.execute(sa.text(
        "UPDATE salary_items SET key='att_bonus', label='全勤/话费补助', "
        "group1='应发金额', group2='基本部分', sort_order=5, is_manual=false "
        "WHERE key='att_award'"))
    op.execute(sa.text(
        "UPDATE salary_items SET label='基本工资', group1='应发金额', group2='基本部分', "
        "sort_order=2 WHERE key='basic'"))
    op.execute(sa.text(
        "UPDATE salary_items SET formula='basic + overtime_pay + att_bonus + subsidy + other_base' "
        "WHERE key='base_total'"))
    op.execute(sa.text("UPDATE salary_items SET is_active=true WHERE key IN "
                       "('attend_days', 'social_company', 'other_company')"))
