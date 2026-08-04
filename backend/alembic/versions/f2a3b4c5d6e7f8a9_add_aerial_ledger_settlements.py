"""add aerial ledger settlement records

Revision ID: f2a3b4c5d6e7f8a9
Revises: e9f0a1b2c3d4e5f6
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f2a3b4c5d6e7f8a9'
down_revision = 'e9f0a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── aerial_ledger_settlements（结算流水：每次登记收款记录一行） ──
    op.create_table(
        'aerial_ledger_settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_method', sa.String(32), nullable=True),
        sa.Column('payment_time', sa.DateTime, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_aerial_ledger_settlements_ledger_id', 'aerial_ledger_settlements', ['ledger_id'])
    # 回填：已登记过收款（实收>0）的台账补一条历史结算记录
    op.execute("""
        INSERT INTO aerial_ledger_settlements
            (id, ledger_id, amount, payment_method, payment_time, remark, created_by, created_at, updated_at)
        SELECT gen_random_uuid(), id, received_amount, payment_method, payment_time, NULL, NULL, updated_at, updated_at
        FROM aerial_daily_ledgers
        WHERE received_amount > 0
    """)


def downgrade() -> None:
    op.drop_index('ix_aerial_ledger_settlements_ledger_id', table_name='aerial_ledger_settlements')
    op.drop_table('aerial_ledger_settlements')
