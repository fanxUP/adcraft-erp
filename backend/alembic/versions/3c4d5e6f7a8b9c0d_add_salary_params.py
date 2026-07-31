"""工资参数：salary_params(参数定义) + salary_param_values(每月取值)；指标增加 is_manual

Revision ID: 3c4d5e6f7a8b9c0d
Revises: a1f2b3c4d5e6f7a8
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '3c4d5e6f7a8b9c0d'
down_revision = 'a1f2b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 手工填写指标列（is_manual=true）：无公式，⚡计算不覆盖
    op.add_column(
        "salary_items",
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "salary_params",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )
    op.create_table(
        "salary_param_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("param_id", UUID(as_uuid=True), sa.ForeignKey("salary_params.id"), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("month", "param_id", name="uq_salary_param_month"),
    )


def downgrade() -> None:
    op.drop_table("salary_param_values")
    op.drop_table("salary_params")
    op.drop_column("salary_items", "is_manual")
