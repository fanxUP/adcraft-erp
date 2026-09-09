"""Add optional planned start/end times to delivery task tables."""

from alembic import op
import sqlalchemy as sa


revision = "n5o6p7q8r9s0"
down_revision = "m4n5o6p7q8r9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("design_tasks", "production_tasks", "installation_tasks"):
        op.add_column(table_name, sa.Column("planned_start_at", sa.DateTime(), nullable=True))
        op.add_column(table_name, sa.Column("planned_end_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table_name in ("installation_tasks", "production_tasks", "design_tasks"):
        op.drop_column(table_name, "planned_end_at")
        op.drop_column(table_name, "planned_start_at")
