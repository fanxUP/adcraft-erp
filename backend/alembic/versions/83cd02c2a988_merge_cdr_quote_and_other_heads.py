"""merge_cdr_quote_and_other_heads

Revision ID: 83cd02c2a988
Revises: 97d60c4ad1c9, e5f6g7h8vehicle
Create Date: 2026-07-27 12:25:36.983633
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83cd02c2a988'
down_revision: Union[str, None] = ('97d60c4ad1c9', 'e5f6g7h8vehicle')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
