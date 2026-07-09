"""add acceptance item area

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acceptance_items", sa.Column("area", sa.Numeric(14, 3), nullable=True))


def downgrade() -> None:
    op.drop_column("acceptance_items", "area")
