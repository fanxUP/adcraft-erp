"""merge heads

Revision ID: 8309d8ebb025
Revises: ad64d94c02a5, 20260709161647
Create Date: 2026-07-09 16:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8309d8ebb025"
down_revision: Union[str, None] = ("ad64d94c02a5", "20260709161647")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
