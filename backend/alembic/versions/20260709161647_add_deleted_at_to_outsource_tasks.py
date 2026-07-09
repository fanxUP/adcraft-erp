"""add deleted_at to outsource_tasks

Revision ID: 20260709161647
Revises: f8a9b0c1d2e3
Create Date: 2026-07-09 16:16:47.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260709161647"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outsource_tasks", sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("outsource_tasks", "deleted_at")
