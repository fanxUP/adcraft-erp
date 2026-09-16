"""Add an optional payment method to operating expenses."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "epm01_expense_payment_method"
down_revision: Union[str, None] = "sup01_supplier_master"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("payment_method", sa.String(length=32), nullable=True, comment="付款方式"),
    )


def downgrade() -> None:
    op.drop_column("expenses", "payment_method")
