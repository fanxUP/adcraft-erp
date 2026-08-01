"""remove employees.base_salary (salary rules are authoritative)

Revision ID: f2a3b4c5d6e7f809
Revises: e0f1a2b3c4d5e6f7
Create Date: 2026-08-01

员工档案里的 base_salary 冗余且从不参与发薪（发薪权威来源是工资规则表），删除该列。
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7f809"
down_revision = "e0f1a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("employees", "base_salary")


def downgrade() -> None:
    op.add_column("employees", sa.Column("base_salary", sa.Numeric(14, 2), nullable=True))
