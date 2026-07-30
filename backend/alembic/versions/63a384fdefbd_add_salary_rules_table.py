"""add_salary_rules_table

Revision ID: 63a384fdefbd
Revises: 63a384fdefbc
Create Date: 2026-07-30 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "63a384fdefbd"
down_revision: Union[str, None] = "63a384fdefbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("salary_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("overtime_rate", sa.Numeric(4, 2), nullable=True),
        sa.Column("bonus_standard", sa.Numeric(14, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("subsidy_standard", sa.Numeric(14, 2), nullable=True),
        sa.Column("attendance_bonus", sa.Numeric(14, 2), nullable=True),
        sa.Column("social_insurance", sa.Numeric(14, 2), nullable=True),
        sa.Column("housing_fund", sa.Numeric(14, 2), nullable=True),
        sa.Column("deduction_standard", sa.Numeric(14, 2), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_salary_rules_employee", "salary_rules", ["employee_id"])


def downgrade() -> None:
    op.drop_index("idx_salary_rules_employee")
    op.drop_table("salary_rules")
