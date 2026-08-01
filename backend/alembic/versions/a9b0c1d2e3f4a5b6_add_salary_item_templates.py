"""工资指标设置模板表 salary_item_templates

Revision ID: a9b0c1d2e3f4a5b6
Revises: b2c3d4e5f6071823
Create Date: 2026-08-01

指标设置弹窗「存为模板」保存的命名快照：items 为 JSON 数组，每个元素
{key, label, formula, sort_order, is_active, is_manual, group1, group2}。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'a9b0c1d2e3f4a5b6'
down_revision = 'b2c3d4e5f6071823'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salary_item_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("items", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("salary_item_templates")
