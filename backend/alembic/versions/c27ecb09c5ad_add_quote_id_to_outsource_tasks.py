"""add_quote_id_to_outsource_tasks

Revision ID: c27ecb09c5ad
Revises: cc23a92b0292
Create Date: 2026-07-09 13:55:27.610246
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c27ecb09c5ad'
down_revision: Union[str, None] = 'cc23a92b0292'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not column_exists("outsource_tasks", "quote_id"):
        op.add_column('outsource_tasks', sa.Column('quote_id', sa.UUID(), nullable=True))
        op.create_foreign_key('fk_outsource_tasks_quote_id', 'outsource_tasks', 'quotes', ['quote_id'], ['id'])


def downgrade() -> None:
    if column_exists("outsource_tasks", "quote_id"):
        op.drop_constraint('fk_outsource_tasks_quote_id', 'outsource_tasks', type_='foreignkey')
        op.drop_column('outsource_tasks', 'quote_id')
