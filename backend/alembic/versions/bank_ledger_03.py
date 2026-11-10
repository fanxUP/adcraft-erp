"""Attribute new customer receipts and project costs to bank ledger requests."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "bank_ledger_03"
down_revision = "bank_ledger_02"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("payments", sa.Column("payment_account_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_payments_payment_account", "payments", "company_accounts",
        ["payment_account_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_payments_payment_account_id", "payments", ["payment_account_id"])
    op.add_column("project_costs", sa.Column("request_id", UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_project_costs_request_id", "project_costs", ["request_id"])


def downgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM payments WHERE payment_account_id IS NOT NULL)
               OR EXISTS (SELECT 1 FROM project_costs WHERE request_id IS NOT NULL) THEN
                RAISE EXCEPTION 'Bank-attributed business records exist; restore from backup to roll back';
            END IF;
        END $$
    """)
    op.drop_constraint("uq_project_costs_request_id", "project_costs", type_="unique")
    op.drop_column("project_costs", "request_id")
    op.drop_index("ix_payments_payment_account_id", table_name="payments")
    op.drop_constraint("fk_payments_payment_account", "payments", type_="foreignkey")
    op.drop_column("payments", "payment_account_id")
