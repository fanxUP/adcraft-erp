"""Add same-order finish-to-start task dependencies."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m4n5o6p7q8r9"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predecessor_task_type", sa.String(length=32), nullable=False),
        sa.Column("predecessor_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("successor_task_type", sa.String(length=32), nullable=False),
        sa.Column("successor_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "dependency_type",
            sa.String(length=32),
            nullable=False,
            server_default="finish_to_start",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_task_dependencies_created_by", ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "predecessor_task_type IN ('design', 'production', 'installation') "
            "AND successor_task_type IN ('design', 'production', 'installation')",
            name="ck_task_dependencies_task_types",
        ),
        sa.CheckConstraint(
            "dependency_type = 'finish_to_start'",
            name="ck_task_dependencies_type",
        ),
        sa.CheckConstraint(
            "predecessor_task_type <> successor_task_type OR predecessor_task_id <> successor_task_id",
            name="ck_task_dependencies_not_self",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "predecessor_task_type",
            "predecessor_task_id",
            "successor_task_type",
            "successor_task_id",
            name="uq_task_dependencies_edge",
        ),
    )
    op.create_index(
        "ix_task_dependencies_successor",
        "task_dependencies",
        ["successor_task_type", "successor_task_id"],
    )
    op.create_index(
        "ix_task_dependencies_predecessor",
        "task_dependencies",
        ["predecessor_task_type", "predecessor_task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_dependencies_predecessor", table_name="task_dependencies")
    op.drop_index("ix_task_dependencies_successor", table_name="task_dependencies")
    op.drop_table("task_dependencies")
