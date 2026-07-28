"""区分常规报价与 CDR 智能报价

Revision ID: r1s2t3u4_add_quote_mode
Revises: phase8_add_ai_assistant_tables
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r1s2t3u4_add_quote_mode"
down_revision: Union[str, None] = "phase8_add_ai_assistant_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("business_documents")}
    if "quote_mode" not in columns:
        op.add_column(
            "business_documents",
            sa.Column(
                "quote_mode",
                sa.String(length=16),
                nullable=False,
                server_default="regular",
                comment="报价模式: regular | cdr",
            ),
        )
    indexes = {index["name"] for index in inspector.get_indexes("business_documents")}
    if "ix_business_documents_quote_mode" not in indexes:
        op.create_index(
            "ix_business_documents_quote_mode",
            "business_documents",
            ["quote_mode"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("business_documents")}
    if "ix_business_documents_quote_mode" in indexes:
        op.drop_index("ix_business_documents_quote_mode", table_name="business_documents")
    columns = {column["name"] for column in inspector.get_columns("business_documents")}
    if "quote_mode" in columns:
        op.drop_column("business_documents", "quote_mode")
