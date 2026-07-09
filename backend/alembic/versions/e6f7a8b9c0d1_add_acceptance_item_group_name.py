"""add acceptance item group_name

Revision ID: e6f7a8b9c0d1
Revises: c3d4e5f6a7b8
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acceptance_items", sa.Column("group_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("acceptance_items", "group_name")
