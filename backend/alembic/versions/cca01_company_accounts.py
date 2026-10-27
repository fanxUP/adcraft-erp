"""Company payment accounts; historical payments remain unassigned."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "cca01_company_accounts"
down_revision = "order_first_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "company_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("holder_name", sa.String(200)),
        sa.Column("bank_name", sa.String(200)),
        sa.Column("account_number", sa.String(200)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("remark", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("account_type IN ('bank', 'wechat', 'alipay', 'cash', 'other')", name="ck_company_account_type"),
        sa.CheckConstraint("NOT is_default OR is_active", name="ck_company_account_default_active"),
    )
    op.create_index("uq_company_account_default", "company_accounts", ["is_default"], unique=True, postgresql_where=sa.text("is_default = true"))
    for table in ("expenses", "project_costs", "payable_payments", "outsource_payments"):
        op.add_column(table, sa.Column("payment_account_id", UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_payment_account", table, "company_accounts", ["payment_account_id"], ["id"], ondelete="RESTRICT")
        op.create_index(f"ix_{table}_payment_account_id", table, ["payment_account_id"])
    # Keep existing payment operators able to choose an account. Account management
    # is granted only to existing administrators/finance; other grants stay intact.
    for action, name in (("select", "选择付款账户"), ("read", "查看公司账户"), ("manage", "管理公司账户"), ("view_number", "查看完整账号")):
        op.execute(sa.text("""
            INSERT INTO permissions (id, code, name, module, resource, action, kind, sensitivity, status, sort_order)
            VALUES (gen_random_uuid(), :code, :name, 'company_account', 'company_account', :action, 'action', 'financial', 'active', 0)
            ON CONFLICT (code) DO NOTHING
        """).bindparams(code=f"company_account:{action}", name=name, action=action))
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE p.code LIKE 'company_account:%' AND (
            r.name IN ('admin', 'finance') OR (p.code = 'company_account:select' AND EXISTS (
                SELECT 1 FROM role_permissions rp JOIN permissions old ON old.id = rp.permission_id
                WHERE rp.role_id = r.id AND old.code IN ('expense:create', 'expense:update', 'outsource_payment:create')
            ))
        ) ON CONFLICT DO NOTHING
    """)


def downgrade():
    # Keeping these additive columns is safe with the old application. Never drop
    # real attribution on an application rollback.
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM company_accounts) THEN
      RAISE EXCEPTION 'Company accounts exist; retain additive schema or export and coordinate recovery';
    END IF; END $$""")
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'company_account:%')")
    op.execute("DELETE FROM permissions WHERE code LIKE 'company_account:%'")
    for table in ("outsource_payments", "payable_payments", "project_costs", "expenses"):
        op.drop_index(f"ix_{table}_payment_account_id", table_name=table)
        op.drop_constraint(f"fk_{table}_payment_account", table, type_="foreignkey")
        op.drop_column(table, "payment_account_id")
    op.drop_index("uq_company_account_default", table_name="company_accounts")
    op.drop_table("company_accounts")
