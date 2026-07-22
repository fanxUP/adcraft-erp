"""ensure all order_no start with S, all quote_no start with O

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-22
"""
from alembic import op

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修复任何订单中错误的前缀（O→S）
    op.execute(
        "UPDATE orders SET order_no = 'S' || substring(order_no from 2) "
        "WHERE order_no LIKE 'O%'"
    )
    # 修复任何报价单中错误的前缀（S→O）
    op.execute(
        "UPDATE quotes SET quote_no = 'O' || substring(quote_no from 2) "
        "WHERE quote_no LIKE 'S%'"
    )


def downgrade() -> None:
    pass
