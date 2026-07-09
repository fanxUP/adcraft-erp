"""add quote_item_id to project_costs

Revision ID: cc23a92b0294
Revises: cc23a92b0293
Create Date: 2026-07-09 19:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cc23a92b0294"
down_revision: Union[str, None] = "cc23a92b0293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_costs", sa.Column("quote_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quote_items.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("project_costs", "quote_item_id")
