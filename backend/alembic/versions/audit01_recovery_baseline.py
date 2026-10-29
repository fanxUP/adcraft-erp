"""Complete the native-install attachment baseline without changing live rows.

Revision ID: audit01_recovery_baseline
Revises: hr01_payroll_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "audit01_recovery_baseline"
down_revision = "hr01_payroll_integrity"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("aerial_vehicle_attachments"):
        op.create_table("aerial_vehicle_attachments",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("vehicle_id", sa.UUID(), sa.ForeignKey("aerial_vehicles.id"), nullable=False),
            sa.Column("attachment_type", sa.String(32), nullable=False, server_default="other"),
            sa.Column("file_url", sa.String(500), nullable=False),
            sa.Column("file_name", sa.String(256)), sa.Column("uploaded_by", sa.UUID()),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("remark", sa.Text()),
        )


def downgrade():
    # A legacy installation may already own this table and all its files.
    # Keeping it is intentional: rollback must never erase those facts.
    pass
