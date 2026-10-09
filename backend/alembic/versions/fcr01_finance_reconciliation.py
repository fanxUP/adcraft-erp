"""Add auditable finance reconciliation records.

Revision ID: fcr01_finance_recon
Revises: sup02_supplier_capabilities
Create Date: 2026-10-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fcr01_finance_recon"
down_revision: Union[str, None] = "sup02_supplier_capabilities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finance_payment_date_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("evidence_reference", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(), nullable=True),
        sa.Column("voided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('expense', 'project_cost', 'outsource_task', 'outsource_payment')",
            name="ck_finance_payment_recon_source_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_finance_payment_recon_amount_positive"),
        sa.CheckConstraint(
            "evidence_type IN ('bank_statement', 'payment_voucher', 'other')",
            name="ck_finance_payment_recon_evidence_type",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="ck_finance_payment_recon_evidence_reference",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_payment_recon_source_active",
        "finance_payment_date_reconciliations",
        ["source_type", "source_id", "voided_at"],
    )
    op.create_index(
        "ix_finance_payment_recon_paid_at",
        "finance_payment_date_reconciliations",
        ["paid_at"],
    )
    op.create_index(
        "uq_finance_payment_recon_active_outsource_payment",
        "finance_payment_date_reconciliations",
        ["source_type", "source_id"],
        unique=True,
        postgresql_where=sa.text("source_type = 'outsource_payment' AND voided_at IS NULL"),
    )

    op.create_table(
        "finance_cost_overlap_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_cost_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outsource_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=True),
        sa.Column("evidence_reference", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "decision IN ('pending', 'confirmed_duplicate', 'confirmed_not_duplicate', 'needs_evidence')",
            name="ck_finance_cost_overlap_review_decision",
        ),
        sa.CheckConstraint(
            "evidence_type IS NULL OR evidence_type IN ('bank_statement', 'payment_voucher', 'other')",
            name="ck_finance_cost_overlap_review_evidence_type",
        ),
        sa.ForeignKeyConstraint(["project_cost_id"], ["project_costs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["outsource_task_id"], ["outsource_tasks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_cost_id", "outsource_task_id", name="uq_finance_cost_overlap_review_pair"),
    )


def downgrade() -> None:
    op.drop_table("finance_cost_overlap_reviews")
    op.drop_index(
        "uq_finance_payment_recon_active_outsource_payment",
        table_name="finance_payment_date_reconciliations",
    )
    op.drop_index("ix_finance_payment_recon_paid_at", table_name="finance_payment_date_reconciliations")
    op.drop_index("ix_finance_payment_recon_source_active", table_name="finance_payment_date_reconciliations")
    op.drop_table("finance_payment_date_reconciliations")
