"""add missing relationship foreign keys

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-09-01

The live database already contains the referenced rows. These constraints
close two gaps found by metadata verification without dropping or rewriting
any existing data.
"""

from alembic import op


revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


FOREIGN_KEYS = (
    (
        "fk_outsource_tasks_related_doc_id",
        "outsource_tasks",
        "business_documents",
        ("related_doc_id",),
        ("id",),
    ),
    (
        "fk_quote_audit_logs_device_id",
        "quote_audit_logs",
        "cdr_devices",
        ("device_id",),
        ("id",),
    ),
)


def upgrade() -> None:
    for name, table, referred_table, columns, referred_columns in FOREIGN_KEYS:
        op.create_foreign_key(name, table, referred_table, list(columns), list(referred_columns))


def downgrade() -> None:
    for name, table, _, _, _ in reversed(FOREIGN_KEYS):
        op.drop_constraint(name, table, type_="foreignkey")
