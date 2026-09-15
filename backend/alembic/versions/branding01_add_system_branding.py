"""Add database-backed application branding."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "branding01_system_branding"
down_revision: Union[str, None] = "eub01_employee_user_binding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_branding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("logo_data", sa.LargeBinary(), nullable=True),
        sa.Column("logo_content_type", sa.String(length=32), nullable=True),
        sa.Column("logo_filename", sa.String(length=255), nullable=True),
        sa.Column("logo_size", sa.Integer(), nullable=True),
        sa.Column("logo_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_system_branding_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_system_branding"),
    )
    op.execute(
        sa.text(
            "INSERT INTO system_branding (id, logo_version, created_at, updated_at) "
            "VALUES (1, 1, now(), now())"
        )
    )


def downgrade() -> None:
    op.drop_table("system_branding")
