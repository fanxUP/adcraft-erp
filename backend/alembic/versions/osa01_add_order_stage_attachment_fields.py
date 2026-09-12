"""Add canonical order/stage ownership to delivery attachments.

Only attachment metadata is backfilled. Physical files are not copied,
renamed, moved, or deleted. The downgrade refuses to remove ownership columns
once canonical rows exist, because doing so would make those files orphaned.
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "osa01_order_stage_attachments"
down_revision: Union[str, None] = "ups01_user_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STAGE_SPECS = (
    ("design_task", "design_tasks", "design"),
    ("production_task", "production_tasks", "production"),
    ("installation_task", "installation_tasks", "installation"),
)


def _column_names(bind) -> set[str]:
    if context.is_offline_mode():
        # Offline SQL generation has no schema inspector.  This migration is
        # published against the revision immediately before it, where these
        # columns do not exist; online execution still performs the exact
        # idempotency check below.
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns("attachments")}


def _foreign_key_names(bind) -> set[str]:
    if context.is_offline_mode():
        return set()
    return {
        key.get("name")
        for key in sa.inspect(bind).get_foreign_keys("attachments")
        if key.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind)
    if "order_id" not in columns:
        op.add_column(
            "attachments",
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "stage" not in columns:
        op.add_column(
            "attachments",
            sa.Column("stage", sa.String(length=32), nullable=True),
        )

    bind = op.get_bind()
    if "fk_attachments_order_id_business_documents" not in _foreign_key_names(bind):
        op.create_foreign_key(
            "fk_attachments_order_id_business_documents",
            "attachments",
            "business_documents",
            ["order_id"],
            ["id"],
        )

    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_attachments_order_stage_created_at "
            "ON attachments (order_id, stage, created_at)"
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_attachments_order_stage'
                ) THEN
                    ALTER TABLE attachments
                    ADD CONSTRAINT ck_attachments_order_stage
                    CHECK (stage IS NULL OR stage IN ('design', 'production', 'installation'));
                END IF;
            END $$
            """
        )
    )

    # Backfill only rows that still use the legacy task polymorphic reference.
    # Keeping related_type/related_id unchanged preserves provenance and lets
    # the compatibility adapter serve older clients during the release window.
    for related_type, table_name, stage in _STAGE_SPECS:
        op.execute(
            sa.text(
                f"""
                UPDATE attachments AS a
                SET order_id = task.document_id,
                    stage = :stage
                FROM {table_name} AS task
                JOIN business_documents AS document
                  ON document.id = task.document_id
                 AND document.doc_type = 'order'
                WHERE a.related_type = :related_type
                  AND a.related_id = task.id
                  AND a.order_id IS NULL
                """
            ).bindparams(
                related_type=related_type,
                stage=stage,
            )
        )


def downgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "订单资料迁移回滚必须在线执行，以先核对仍存的订单级附件数据"
        )
    bind = op.get_bind()
    canonical_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM attachments "
            "WHERE order_id IS NOT NULL OR related_type = 'order_stage'"
        )
    ).scalar_one()
    if canonical_count:
        raise RuntimeError(
            "不能回滚订单资料归属字段：attachments 中仍有订单级资料；"
            "请先恢复应用版本并制定附件元数据恢复方案"
        )

    op.execute(sa.text("ALTER TABLE attachments DROP CONSTRAINT IF EXISTS ck_attachments_order_stage"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_attachments_order_stage_created_at"))
    bind = op.get_bind()
    if "fk_attachments_order_id_business_documents" in _foreign_key_names(bind):
        op.drop_constraint(
            "fk_attachments_order_id_business_documents",
            "attachments",
            type_="foreignkey",
        )
    columns = _column_names(bind)
    if "stage" in columns:
        op.drop_column("attachments", "stage")
    if "order_id" in columns:
        op.drop_column("attachments", "order_id")
