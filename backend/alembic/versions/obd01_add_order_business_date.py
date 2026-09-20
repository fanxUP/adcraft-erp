"""Add the auditable business date for orders."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "obd01_order_business_date"
down_revision: Union[str, None] = "epm01_expense_payment_method"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_documents",
        sa.Column("order_date", sa.Date(), nullable=True, comment="订单业务下单日期；created_at 为系统写入时间，不可替代"),
    )
    # Keep the historical displayed day stable.  The production migration
    # gate must verify the database timezone/storage convention before apply.
    op.execute(
        sa.text(
            """
            UPDATE business_documents
            SET order_date = created_at::date
            WHERE doc_type = 'order'
              AND order_date IS NULL
              AND created_at IS NOT NULL
            """
        )
    )
    op.create_index(
        "ix_business_documents_order_date",
        "business_documents",
        ["order_date"],
        postgresql_where=sa.text("doc_type = 'order' AND deleted_at IS NULL"),
    )
    op.create_check_constraint(
        "ck_business_documents_order_date_for_orders",
        "business_documents",
        "doc_type <> 'order' OR order_date IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_business_documents_order_date_for_orders",
        "business_documents",
        type_="check",
    )
    op.drop_index(
        "ix_business_documents_order_date",
        table_name="business_documents",
    )
    op.drop_column("business_documents", "order_date")
