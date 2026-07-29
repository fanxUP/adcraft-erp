"""为产品材质工艺主数据增加材质和工艺字段。

Revision ID: c8d9e0f1a2b3
Revises: b5c6d7e8f9a0
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d9e0f1a2b3"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("material_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("process_name", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "process_name")
    op.drop_column("products", "material_name")
