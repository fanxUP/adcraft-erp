"""Add unified payable payment ledger.

Revision ID: cpa01_payable_ledger
Revises: cbr01_payment_allocations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cpa01_payable_ledger"
down_revision: Union[str, None] = "cbr01_payment_allocations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("payee_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "expenses",
        sa.Column(
            "payable_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_expenses_payable_amount_range",
        "expenses",
        "payable_amount >= 0 AND payable_amount <= amount",
    )

    op.create_table(
        "payable_payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("payment_no", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("paid_at", sa.DateTime, nullable=False),
        sa.Column("remark", sa.Text, nullable=True),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column(
            "is_voided",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("void_reason", sa.Text, nullable=True),
        sa.Column("voided_at", sa.DateTime, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("payment_no", name="uq_payable_payments_payment_no"),
        sa.CheckConstraint(
            "source_type IN ('expense', 'project_cost')",
            name="ck_payable_payments_source_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_payable_payments_amount_positive"),
    )
    op.create_index(
        "ix_payable_payments_source",
        "payable_payments",
        ["source_type", "source_id", "paid_at"],
    )
    op.create_index(
        "ix_payable_payments_active",
        "payable_payments",
        ["is_voided", "paid_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    payment_count = bind.execute(
        sa.text("SELECT count(*) FROM payable_payments")
    ).scalar_one()
    if payment_count:
        raise RuntimeError(
            "不能回滚应付付款流水：payable_payments 中已有付款事实；"
            "请先完成应用版本回退和应付数据迁移方案。"
        )
    op.drop_index("ix_payable_payments_active", table_name="payable_payments")
    op.drop_index("ix_payable_payments_source", table_name="payable_payments")
    op.drop_table("payable_payments")
    op.drop_constraint(
        "ck_expenses_payable_amount_range",
        "expenses",
        type_="check",
    )
    op.drop_column("expenses", "payable_amount")
    op.drop_column("expenses", "payee_name")
