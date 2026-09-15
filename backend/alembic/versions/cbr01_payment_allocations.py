"""Add contract-scoped payment allocations.

Revision ID: cbr01_payment_allocations
Revises: osa02_attachment_order_item
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cbr01_payment_allocations"
down_revision: Union[str, None] = "osa02_attachment_order_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "payments",
        "document_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "payment_allocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("allocated_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "allocation_type",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'order'"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["business_documents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.CheckConstraint("allocated_amount > 0", name="ck_payment_allocations_amount_positive"),
        sa.CheckConstraint(
            "allocation_type IN ('order', 'contract')",
            name="ck_payment_allocations_type",
        ),
        sa.CheckConstraint(
            "(allocation_type = 'contract' AND document_id IS NULL) "
            "OR (allocation_type = 'order' AND document_id IS NOT NULL)",
            name="ck_payment_allocations_scope",
        ),
    )
    op.create_index(
        "ix_payment_allocations_contract_id",
        "payment_allocations",
        ["contract_id", "created_at"],
    )
    op.create_index(
        "ix_payment_allocations_document_id",
        "payment_allocations",
        ["document_id", "created_at"],
    )
    op.create_index(
        "ix_payment_allocations_payment_id",
        "payment_allocations",
        ["payment_id"],
    )

    # Backfill only unambiguous historical order → contract relations. If a
    # document is linked to more than one active contract, leave it untouched
    # for a later human reconciliation instead of guessing.
    op.execute(
        sa.text(
            """
            WITH linked AS (
                SELECT cd.document_id, cd.contract_id
                FROM contract_documents cd
                JOIN contracts c ON c.id = cd.contract_id
                WHERE c.deleted_at IS NULL
                UNION
                SELECT fcpd.document_id, fcp.contract_id
                FROM framework_contract_project_documents fcpd
                JOIN framework_contract_projects fcp ON fcp.id = fcpd.project_id
                JOIN contracts c ON c.id = fcp.contract_id
                WHERE fcp.deleted_at IS NULL AND c.deleted_at IS NULL
            ), unique_links AS (
                SELECT document_id, min(contract_id) AS contract_id
                FROM linked
                GROUP BY document_id
                HAVING count(DISTINCT contract_id) = 1
            )
            INSERT INTO payment_allocations
                (id, payment_id, contract_id, document_id, allocated_amount,
                 allocation_type, created_at, updated_at)
            SELECT gen_random_uuid(), p.id, ul.contract_id, p.document_id,
                   p.amount, 'order', COALESCE(p.created_at, now()),
                   COALESCE(p.updated_at, now())
            FROM payments p
            JOIN unique_links ul ON ul.document_id = p.document_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM payment_allocations pa
                WHERE pa.payment_id = p.id
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    allocation_count = bind.execute(
        sa.text("SELECT count(*) FROM payment_allocations")
    ).scalar_one()
    if allocation_count:
        raise RuntimeError(
            "不能回滚收款分配：payment_allocations 中已有收款归属事实；"
            "请先完成应用版本回退和收款数据迁移方案。"
        )
    null_document_count = bind.execute(
        sa.text("SELECT count(*) FROM payments WHERE document_id IS NULL")
    ).scalar_one()
    if null_document_count:
        raise RuntimeError(
            "不能回滚 payments.document_id：已有合同级收款没有订单兼容关联。"
        )
    op.drop_index("ix_payment_allocations_payment_id", table_name="payment_allocations")
    op.drop_index("ix_payment_allocations_document_id", table_name="payment_allocations")
    op.drop_index("ix_payment_allocations_contract_id", table_name="payment_allocations")
    op.drop_table("payment_allocations")
    op.alter_column(
        "payments",
        "document_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
