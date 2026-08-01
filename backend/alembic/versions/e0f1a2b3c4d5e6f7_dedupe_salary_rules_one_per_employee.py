"""salary rules: one rule per employee (dedupe + unique constraint)

Revision ID: e0f1a2b3c4d5e6f7
Revises: d4e5f6a7b8c9d0e1
Create Date: 2026-08-01

同一员工只保留最新一条工资规则（effective_date 最新，其次 created_at 最新），
并加 employee_id 唯一约束，从数据库层面保证「一人一条」。
"""
from alembic import op

revision = "e0f1a2b3c4d5e6f7"
down_revision = "d4e5f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 清理重复：同 employee_id 只保留最新一条
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY employee_id
                       ORDER BY effective_date DESC, created_at DESC, id
                   ) AS rn
            FROM salary_rules
        )
        DELETE FROM salary_rules WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """)
    op.create_unique_constraint("uq_salary_rules_employee", "salary_rules", ["employee_id"])


def downgrade() -> None:
    # 不恢复已删除的历史规则（不可逆清理），仅移除唯一约束
    op.drop_constraint("uq_salary_rules_employee", "salary_rules", type_="unique")
