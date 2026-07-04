"""add quote item image_url

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quote_items", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_items", "image_url")
