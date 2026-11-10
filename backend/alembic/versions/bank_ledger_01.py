"""Add opening balances and manual company account ledger entries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "bank_ledger_01"
down_revision = "bf01_payable_request"
branch_labels = None
depends_on = None

PERMISSIONS = {
    "company_account:ledger_read": "查看账户台账和余额",
    "company_account:ledger_create": "登记账户台账",
    "company_account:opening_balance_set": "设置账户期初余额",
}


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "bank_ledger_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("company_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("summary", sa.String(255)),
        sa.Column("counterparty_account", sa.String(200)),
        sa.Column("counterparty_name", sa.String(200)),
        sa.Column("category", sa.String(64)),
        sa.Column("project_name", sa.String(255)),
        sa.Column("department", sa.String(255)),
        sa.Column("request_id", UUID(as_uuid=True), unique=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "entry_type IN ('opening_balance', 'manual')",
            name="ck_bank_ledger_entry_type",
        ),
        sa.CheckConstraint(
            "direction IN ('opening', 'income', 'expense')",
            name="ck_bank_ledger_direction",
        ),
        sa.CheckConstraint(
            "(entry_type = 'opening_balance' AND direction = 'opening' AND amount >= 0) "
            "OR (entry_type = 'manual' AND direction IN ('income', 'expense') AND amount > 0)",
            name="ck_bank_ledger_amount_and_direction",
        ),
    )
    op.create_index(
        "ix_bank_ledger_account_date", "bank_ledger_entries", ["account_id", "entry_date"]
    )
    op.create_index(
        "uq_bank_ledger_opening_per_account",
        "bank_ledger_entries",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text("entry_type = 'opening_balance'"),
    )

    for code, name in PERMISSIONS.items():
        action = code.split(":", 1)[1]
        op.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (id, code, name, module, resource, action, kind, sensitivity, status, sort_order)
                VALUES
                    (gen_random_uuid(), :code, :name, 'company_account', 'company_account',
                     :action, 'action', 'financial', 'active', 0)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(code=code, name=name, action=action)
        )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('admin', 'finance')
          AND p.code IN (
              'company_account:ledger_read',
              'company_account:ledger_create',
              'company_account:opening_balance_set'
          )
        ON CONFLICT DO NOTHING
        """
    )


def downgrade():
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM bank_ledger_entries) THEN
                RAISE EXCEPTION 'Bank ledger entries exist; retain ledger data during rollback';
            END IF;
        END $$
        """
    )
    op.drop_index("uq_bank_ledger_opening_per_account", table_name="bank_ledger_entries")
    op.drop_index("ix_bank_ledger_account_date", table_name="bank_ledger_entries")
    op.drop_table("bank_ledger_entries")
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE code IN (
                'company_account:ledger_read',
                'company_account:ledger_create',
                'company_account:opening_balance_set'
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE code IN (
            'company_account:ledger_read',
            'company_account:ledger_create',
            'company_account:opening_balance_set'
        )
        """
    )
