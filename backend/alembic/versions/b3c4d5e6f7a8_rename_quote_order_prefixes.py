"""rename quote/order number prefixes: SO→O for quotes, SO→S for orders, Q→O for quotes

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-22
"""
from alembic import op

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 报价单：SO→O
    op.execute(
        "UPDATE quotes SET quote_no = 'O' || substring(quote_no from 3) "
        "WHERE quote_no LIKE 'SO%'"
    )
    # 报价单：Q→O（之前改为Q前缀的）
    op.execute(
        "UPDATE quotes SET quote_no = 'O' || substring(quote_no from 2) "
        "WHERE quote_no LIKE 'Q%'"
    )
    # 订单：SO→S
    op.execute(
        "UPDATE orders SET order_no = 'S' || substring(order_no from 3) "
        "WHERE order_no LIKE 'SO%'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE quotes SET quote_no = 'SO' || substring(quote_no from 2) "
        "WHERE quote_no LIKE 'O%'"
    )
    op.execute(
        "UPDATE orders SET order_no = 'SO' || substring(order_no from 2) "
        "WHERE order_no LIKE 'S%'"
    )
