"""replace_quote_id_with_related_doc_fields

Revision ID: 6d88d54999c7
Revises: c27ecb09c5ad
Create Date: 2026-07-09 14:24:53.657374
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '6d88d54999c7'
down_revision: Union[str, None] = 'c27ecb09c5ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    # Drop quote_id column and its FK constraint
    if column_exists("outsource_tasks", "quote_id"):
        op.drop_constraint('fk_outsource_tasks_quote_id', 'outsource_tasks', type_='foreignkey')
        op.drop_column('outsource_tasks', 'quote_id')

    # Add related_doc_id and related_doc_type
    if not column_exists("outsource_tasks", "related_doc_id"):
        op.add_column('outsource_tasks', sa.Column('related_doc_id', sa.UUID(), nullable=True))
    if not column_exists("outsource_tasks", "related_doc_type"):
        op.add_column('outsource_tasks', sa.Column('related_doc_type', sa.String(length=16), nullable=True))


def downgrade() -> None:
    if column_exists("outsource_tasks", "related_doc_type"):
        op.drop_column('outsource_tasks', 'related_doc_type')
    if column_exists("outsource_tasks", "related_doc_id"):
        op.drop_column('outsource_tasks', 'related_doc_id')
    if not column_exists("outsource_tasks", "quote_id"):
        op.add_column('outsource_tasks', sa.Column('quote_id', sa.UUID(), nullable=True))
        op.create_foreign_key('fk_outsource_tasks_quote_id', 'outsource_tasks', 'quotes', ['quote_id'], ['id'])
