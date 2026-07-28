"""为派车单增加随车人员。

Revision ID: a4c8e2f6b901
Revises: f2a9c7d1e4b6
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "a4c8e2f6b901"
down_revision = "f2a9c7d1e4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle_dispatches",
        sa.Column("companions", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicle_dispatches", "companions")
