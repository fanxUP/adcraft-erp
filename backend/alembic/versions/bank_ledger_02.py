"""Link manual bank ledger entries to suppliers and orders."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "bank_ledger_02"
down_revision = "bank_ledger_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.alter_column(
        "bank_ledger_entries",
        "counterparty_name",
        existing_type=sa.String(length=200),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.add_column(
        "bank_ledger_entries",
        sa.Column("counterparty_supplier_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "bank_ledger_entries",
        sa.Column("order_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_ledger_supplier",
        "bank_ledger_entries",
        "outsource_vendors",
        ["counterparty_supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_bank_ledger_order",
        "bank_ledger_entries",
        "business_documents",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_bank_ledger_supplier_id", "bank_ledger_entries", ["counterparty_supplier_id"]
    )
    op.create_index("ix_bank_ledger_order_id", "bank_ledger_entries", ["order_id"])


def downgrade():
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM bank_ledger_entries
                WHERE char_length(counterparty_name) > 200
            ) THEN
                RAISE EXCEPTION 'Ledger counterparty names exceed 200 characters; retain the wider column';
            END IF;
        END $$
        """
    )
    op.drop_index("ix_bank_ledger_order_id", table_name="bank_ledger_entries")
    op.drop_index("ix_bank_ledger_supplier_id", table_name="bank_ledger_entries")
    op.drop_constraint("fk_bank_ledger_order", "bank_ledger_entries", type_="foreignkey")
    op.drop_constraint("fk_bank_ledger_supplier", "bank_ledger_entries", type_="foreignkey")
    op.drop_column("bank_ledger_entries", "order_id")
    op.drop_column("bank_ledger_entries", "counterparty_supplier_id")
    op.alter_column(
        "bank_ledger_entries",
        "counterparty_name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=200),
        existing_nullable=True,
    )
