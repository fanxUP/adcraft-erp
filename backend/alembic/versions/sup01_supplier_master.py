"""Add unified supplier master fields and source links.

Revision ID: sup01_supplier_master
Revises: cpa01_payable_ledger

The existing ``outsource_vendors`` table is intentionally extended instead of
creating a second supplier table.  Legacy external vendors receive the
``outsource`` type.  Historical text payees are linked only when the trimmed
name matches exactly one active supplier.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "sup01_supplier_master"
down_revision: Union[str, None] = "cpa01_payable_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outsource_vendors",
        sa.Column(
            "supplier_type",
            sa.String(length=32),
            nullable=True,
            server_default=sa.text("'outsource'"),
        ),
    )
    op.add_column("outsource_vendors", sa.Column("short_name", sa.String(length=128), nullable=True))
    op.add_column("outsource_vendors", sa.Column("tax_id", sa.String(length=64), nullable=True))
    op.add_column("outsource_vendors", sa.Column("email", sa.String(length=128), nullable=True))
    op.add_column("outsource_vendors", sa.Column("bank_name", sa.String(length=128), nullable=True))
    op.add_column("outsource_vendors", sa.Column("bank_account", sa.String(length=128), nullable=True))
    op.add_column("outsource_vendors", sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column("outsource_vendors", sa.Column("settlement_method", sa.String(length=32), nullable=True))
    op.add_column("outsource_vendors", sa.Column("settlement_days", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE outsource_vendors "
            "SET supplier_type = 'outsource' "
            "WHERE supplier_type IS NULL"
        )
    )
    op.alter_column(
        "outsource_vendors",
        "supplier_type",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default=None,
    )
    op.create_index(
        "ix_outsource_vendors_supplier_type",
        "outsource_vendors",
        ["supplier_type"],
    )
    op.create_index(
        "ix_outsource_vendors_active_name",
        "outsource_vendors",
        ["is_active", "name"],
    )
    op.create_check_constraint(
        "ck_outsource_vendors_tax_rate_range",
        "outsource_vendors",
        "tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100)",
    )
    op.create_check_constraint(
        "ck_outsource_vendors_settlement_days_range",
        "outsource_vendors",
        "settlement_days IS NULL OR (settlement_days >= 0 AND settlement_days <= 3650)",
    )

    uuid_type = postgresql.UUID(as_uuid=True)
    op.add_column("project_costs", sa.Column("supplier_id", uuid_type, nullable=True))
    op.add_column("expenses", sa.Column("supplier_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_project_costs_supplier_id",
        "project_costs",
        "outsource_vendors",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expenses_supplier_id",
        "expenses",
        "outsource_vendors",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_project_costs_supplier_id", "project_costs", ["supplier_id"])
    op.create_index("ix_expenses_supplier_id", "expenses", ["supplier_id"])

    # Conservative historical backfill: only active, non-deleted suppliers
    # with one exact trimmed name are eligible.  Ambiguous names stay as the
    # legacy payee text and can be linked manually from the UI.
    op.execute(
        sa.text(
            "UPDATE project_costs AS pc "
            "SET supplier_id = ov.id "
            "FROM outsource_vendors AS ov "
            "WHERE pc.supplier_id IS NULL "
            "AND pc.payee_company_name IS NOT NULL "
            "AND btrim(pc.payee_company_name) <> '' "
            "AND btrim(pc.payee_company_name) = btrim(ov.name) "
            "AND ov.deleted_at IS NULL "
            "AND ov.is_active = true "
            "AND (SELECT count(*) FROM outsource_vendors AS ov2 "
            "     WHERE ov2.deleted_at IS NULL AND ov2.is_active = true "
            "     AND btrim(ov2.name) = btrim(pc.payee_company_name)) = 1"
        )
    )
    op.execute(
        sa.text(
            "UPDATE expenses AS e "
            "SET supplier_id = ov.id "
            "FROM outsource_vendors AS ov "
            "WHERE e.supplier_id IS NULL "
            "AND e.payee_name IS NOT NULL "
            "AND btrim(e.payee_name) <> '' "
            "AND btrim(e.payee_name) = btrim(ov.name) "
            "AND ov.deleted_at IS NULL "
            "AND ov.is_active = true "
            "AND (SELECT count(*) FROM outsource_vendors AS ov2 "
            "     WHERE ov2.deleted_at IS NULL AND ov2.is_active = true "
            "     AND btrim(ov2.name) = btrim(e.payee_name)) = 1"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    linked_costs = bind.execute(
        sa.text("SELECT count(*) FROM project_costs WHERE supplier_id IS NOT NULL")
    ).scalar_one()
    linked_expenses = bind.execute(
        sa.text("SELECT count(*) FROM expenses WHERE supplier_id IS NOT NULL")
    ).scalar_one()
    if linked_costs or linked_expenses:
        raise RuntimeError(
            "不能回滚供应商主数据：项目成本或经营支出已有供应商关联；"
            "请先完成应用版本回退和关联数据迁移。"
        )

    op.drop_index("ix_expenses_supplier_id", table_name="expenses")
    op.drop_index("ix_project_costs_supplier_id", table_name="project_costs")
    op.drop_constraint("fk_expenses_supplier_id", "expenses", type_="foreignkey")
    op.drop_constraint("fk_project_costs_supplier_id", "project_costs", type_="foreignkey")
    op.drop_column("expenses", "supplier_id")
    op.drop_column("project_costs", "supplier_id")
    op.drop_constraint(
        "ck_outsource_vendors_settlement_days_range",
        "outsource_vendors",
        type_="check",
    )
    op.drop_constraint(
        "ck_outsource_vendors_tax_rate_range",
        "outsource_vendors",
        type_="check",
    )
    op.drop_index("ix_outsource_vendors_active_name", table_name="outsource_vendors")
    op.drop_index("ix_outsource_vendors_supplier_type", table_name="outsource_vendors")
    for column in (
        "settlement_days",
        "settlement_method",
        "tax_rate",
        "bank_account",
        "bank_name",
        "email",
        "tax_id",
        "short_name",
        "supplier_type",
    ):
        op.drop_column("outsource_vendors", column)
