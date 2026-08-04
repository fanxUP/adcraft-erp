"""add payee to aerial ledger settlements

Revision ID: b9c8d7e6f5a4b3c2
Revises: f2a3b4c5d6e7f8a9
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b9c8d7e6f5a4b3c2'
down_revision = 'f2a3b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 结算流水新增收款人（人员外键，可空） ──
    op.add_column(
        'aerial_ledger_settlements',
        sa.Column('payee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_personnel.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('aerial_ledger_settlements', 'payee_id')
