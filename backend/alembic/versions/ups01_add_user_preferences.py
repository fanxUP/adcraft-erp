"""Add per-user UI preferences with safe defaults."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ups01_user_preferences"
down_revision: Union[str, None] = "tio01_task_item_assignees"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "theme",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'light-blue'"),
        ),
        sa.Column(
            "font_size",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("14"),
        ),
        sa.Column(
            "font_weight",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("400"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_preferences_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_preferences"),
    )

    # Backfill existing accounts without copying any browser-local setting.
    # The insert is idempotent so a repaired or partially applied environment
    # can safely rerun the data step inside the migration transaction.
    op.execute(
        sa.text(
            """
            INSERT INTO user_preferences (user_id, theme, font_size, font_weight, created_at, updated_at)
            SELECT u.id, 'light-blue', 14, 400, now(), now()
            FROM users AS u
            WHERE NOT EXISTS (
                SELECT 1
                FROM user_preferences AS p
                WHERE p.user_id = u.id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
