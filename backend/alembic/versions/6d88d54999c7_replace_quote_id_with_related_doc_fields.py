"""replace_quote_id_with_related_doc_fields

Revision ID: 6d88d54999c7
Revises: c27ecb09c5ad
Create Date: 2026-07-09 14:24:53.657374
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '6d88d54999c7'
down_revision: Union[str, None] = 'c27ecb09c5ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    return column in [c["name"] for c in inspector.get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Drop any FK on quote_id regardless of naming
    if column_exists("outsource_tasks", "quote_id"):
        for fk in inspector.get_foreign_keys("outsource_tasks"):
            if "quote_id" in fk["constrained_columns"]:
                op.drop_constraint(fk["name"], "outsource_tasks", type_="foreignkey")
        op.drop_column('outsource_tasks', 'quote_id')

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
