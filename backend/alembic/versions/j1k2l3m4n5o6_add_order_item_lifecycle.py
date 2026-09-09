"""add lifecycle fields for business document items

Revision ID: j1k2l3m4n5o6
Revises: i3j4k5l6m7n8
Create Date: 2026-09-02

The lifecycle is additive. Existing rows become active; associated rows can
then be voided without breaking historical foreign-key references.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "j1k2l3m4n5o6"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_document_items",
        sa.Column(
            "lifecycle_status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "business_document_items",
        sa.Column("voided_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "business_document_items",
        sa.Column("void_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "business_document_items",
        sa.Column(
            "superseded_by_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_business_document_items_superseded_by",
        "business_document_items",
        "business_document_items",
        ["superseded_by_item_id"],
        ["id"],
    )
    op.create_index(
        "ix_business_document_items_lifecycle_status",
        "business_document_items",
        ["lifecycle_status"],
    )
    op.create_index(
        "ix_business_document_items_superseded_by_item_id",
        "business_document_items",
        ["superseded_by_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_document_items_superseded_by_item_id",
        table_name="business_document_items",
    )
    op.drop_index(
        "ix_business_document_items_lifecycle_status",
        table_name="business_document_items",
    )
    op.drop_constraint(
        "fk_business_document_items_superseded_by",
        "business_document_items",
        type_="foreignkey",
    )
    op.drop_column("business_document_items", "superseded_by_item_id")
    op.drop_column("business_document_items", "void_reason")
    op.drop_column("business_document_items", "voided_at")
    op.drop_column("business_document_items", "lifecycle_status")
