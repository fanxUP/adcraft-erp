"""add indexes on business-chain FK columns

Revision ID: f1a2b3c4d5e6
Revises: e7a8b9c0d1e2
Create Date: 2026-08-16
"""
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e7a8b9c0d1e2"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_items_document", "business_document_items", ["document_id"]),
    ("ix_payments_document", "payments", ["document_id"]),
    ("ix_payments_customer", "payments", ["customer_id"]),
    ("ix_design_document", "design_tasks", ["document_id"]),
    ("ix_design_customer", "design_tasks", ["customer_id"]),
    ("ix_production_document", "production_tasks", ["document_id"]),
    ("ix_production_customer", "production_tasks", ["customer_id"]),
    ("ix_installation_document", "installation_tasks", ["document_id"]),
    ("ix_installation_customer", "installation_tasks", ["customer_id"]),
    ("ix_outsource_doc", "outsource_tasks", ["related_doc_id"]),
    ("ix_outsource_source", "outsource_tasks", ["source_task_type", "source_task_id"]),
    ("ix_outsource_vendor", "outsource_tasks", ["vendor_id"]),
    ("ix_acceptance_doc", "acceptance_forms", ["document_id"]),
    ("ix_accept_items", "acceptance_items", ["acceptance_id"]),
]


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, cols in INDEXES:
        op.drop_index(name, table_name=table)
