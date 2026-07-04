"""add acceptance discount and advance amounts

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acceptance_forms", sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("acceptance_forms", sa.Column("advance_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("acceptance_forms", "advance_amount")
    op.drop_column("acceptance_forms", "discount_amount")
