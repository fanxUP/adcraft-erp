"""Track the bank source of receipts and the archive batch of legacy receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "receivables_bank_01"
down_revision = "bank_ledger_06"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("bank_ledger_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payments", sa.Column("archive_batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_payments_bank_ledger_entry", "payments", "bank_ledger_entries",
        ["bank_ledger_entry_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_payments_bank_ledger_entry_id", "payments", ["bank_ledger_entry_id"])
    op.create_index(
        "uq_payments_active_bank_ledger_entry",
        "payments",
        ["bank_ledger_entry_id"],
        unique=True,
        postgresql_where=sa.text(
            "bank_ledger_entry_id IS NOT NULL AND is_voided IS FALSE AND archive_batch_id IS NULL"
        ),
    )


def downgrade():
    state = op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM payments "
        "WHERE bank_ledger_entry_id IS NOT NULL OR archive_batch_id IS NOT NULL)"
    )).scalar()
    if state:
        raise RuntimeError("已有银行流水关联或收款归档，请先按迁移方案核对并恢复数据")
    op.drop_index("uq_payments_active_bank_ledger_entry", table_name="payments")
    op.drop_index("ix_payments_bank_ledger_entry_id", table_name="payments")
    op.drop_constraint("fk_payments_bank_ledger_entry", "payments", type_="foreignkey")
    op.drop_column("payments", "archive_batch_id")
    op.drop_column("payments", "bank_ledger_entry_id")
