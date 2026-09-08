"""Add multi-item project-cost scope links without amount allocation."""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t3u4v5w6x7y8"
down_revision: Union[str, None] = "q8r9s0t1u2v3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_cost_item_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_cost_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_cost_id"],
            ["project_costs.id"],
            name="fk_project_cost_item_links_cost",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_item_id"],
            ["business_document_items.id"],
            name="fk_project_cost_item_links_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "project_cost_id",
            "document_item_id",
            name="uq_project_cost_item_link",
        ),
    )
    op.create_index(
        "ix_project_cost_item_links_cost",
        "project_cost_item_links",
        ["project_cost_id"],
    )
    op.create_index(
        "ix_project_cost_item_links_item",
        "project_cost_item_links",
        ["document_item_id"],
    )

    # Deterministic compatibility backfill only: an existing single-valued
    # association maps to exactly one link. NULL remains whole-order scope.
    op.execute(
        sa.text(
            """
            INSERT INTO project_cost_item_links (
                id, project_cost_id, document_item_id, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                pc.id,
                pc.document_item_id,
                COALESCE(pc.created_at, now()),
                COALESCE(pc.updated_at, now())
            FROM project_costs pc
            WHERE pc.document_item_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM project_cost_item_links link
                  WHERE link.project_cost_id = pc.id
                    AND link.document_item_id = pc.document_item_id
              )
            """
        )
    )


def downgrade() -> None:
    # A multi-item association cannot be represented by the legacy singular
    # column without losing information. Release recovery should restore the
    # pre-migration database backup when this table contains multi-item rows.
    if not context.is_offline_mode():
        bind = op.get_bind()
        multi_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM project_cost_item_links link
                WHERE (
                    SELECT COUNT(*)
                    FROM project_cost_item_links same_cost
                    WHERE same_cost.project_cost_id = link.project_cost_id
                ) > 1
                """
            )
        ).scalar_one()
        if multi_count:
            raise RuntimeError(
                "不能降级：project_cost_item_links 已存在多明细成本关系，请使用发布前备份恢复"
            )
    op.drop_index("ix_project_cost_item_links_item", table_name="project_cost_item_links")
    op.drop_index("ix_project_cost_item_links_cost", table_name="project_cost_item_links")
    op.drop_table("project_cost_item_links")
