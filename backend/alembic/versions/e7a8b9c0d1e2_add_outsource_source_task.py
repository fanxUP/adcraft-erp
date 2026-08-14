"""add source_task_type/source_task_id to outsource_tasks

Revision ID: e7a8b9c0d1e2
Revises: b0c1d2e3f4a5
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e7a8b9c0d1e2"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("outsource_tasks", sa.Column("source_task_type", sa.String(32), nullable=True, comment="来源内部任务类型"))
    op.add_column("outsource_tasks", sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True, comment="来源内部任务 id"))

def downgrade() -> None:
    op.drop_column("outsource_tasks", "source_task_id")
    op.drop_column("outsource_tasks", "source_task_type")
