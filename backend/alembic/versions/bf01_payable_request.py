"""Idempotency for new payable payments; historical facts are unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "bf01_payable_request"
down_revision = "audit01_recovery_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payable_payments", sa.Column("request_id", sa.UUID(), nullable=True))
    op.add_column("payable_payments", sa.Column("request_digest", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_payable_payments_request_id", "payable_payments", ["request_id"])


def downgrade():
    # Keep payment amounts, dates and rows. Only retry metadata is removed.
    op.drop_constraint("uq_payable_payments_request_id", "payable_payments", type_="unique")
    op.drop_column("payable_payments", "request_digest")
    op.drop_column("payable_payments", "request_id")
