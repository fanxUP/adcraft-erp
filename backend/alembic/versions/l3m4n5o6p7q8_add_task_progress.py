"""Add independent progress percentages to delivery tasks."""

from alembic import op
import sqlalchemy as sa


revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    task_tables = (
        ("design_tasks", ("confirmed", "completed")),
        ("production_tasks", ("completed",)),
        ("installation_tasks", ("completed",)),
    )
    for table, terminal_statuses in task_tables:
        op.add_column(
            table,
            sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        )
        quoted_statuses = ", ".join(f"'{status}'" for status in terminal_statuses)
        op.execute(
            sa.text(
                f"UPDATE {table} SET progress_pct = 100 "
                f"WHERE status IN ({quoted_statuses})"
            )
        )
        op.alter_column(table, "progress_pct", server_default=None)


def downgrade() -> None:
    for table in ("installation_tasks", "production_tasks", "design_tasks"):
        op.drop_column(table, "progress_pct")
