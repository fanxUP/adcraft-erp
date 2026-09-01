"""persist business-document group definitions, including empty groups

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_document_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.String(length=255), nullable=False),
        sa.Column("group_name", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["business_documents.id"]),
        sa.UniqueConstraint("document_id", "group_id", name="uq_business_document_group"),
    )
    op.create_index(
        "ix_business_document_groups_document",
        "business_document_groups",
        ["document_id"],
    )

    # Backfill definitions from existing grouped detail rows. The first
    # appearance of a group determines its display order.
    op.execute(sa.text("""
        INSERT INTO business_document_groups
            (document_id, group_id, group_name, sort_order)
        SELECT
            document_id,
            group_id,
            MAX(group_name),
            MIN(sort_order)
        FROM business_document_items
        WHERE group_id IS NOT NULL
        GROUP BY document_id, group_id
    """))


def downgrade() -> None:
    op.drop_index(
        "ix_business_document_groups_document",
        table_name="business_document_groups",
    )
    op.drop_table("business_document_groups")
