"""Support associating one delivery task with multiple order items."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "p7q8r9s0t1u2"
down_revision = "o6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("task_order_item_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["business_document_items.id"],
            name="fk_task_order_item_links_order_item_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_type",
            "task_id",
            "order_item_id",
            name="uq_task_order_item_link",
        ),
    )
    op.create_index(
        "ix_task_order_item_link_task",
        "task_order_item_links",
        ["task_type", "task_id"],
    )
    op.create_index(
        "ix_task_order_item_link_item",
        "task_order_item_links",
        ["order_item_id"],
    )

    # Copy only explicit legacy links. An unlinked historical task remains unlinked.
    op.execute(
        sa.text(
            """
            INSERT INTO task_order_item_links
                (id, task_type, task_id, order_item_id, position)
            SELECT gen_random_uuid(), 'design', id, order_item_id, 0
            FROM design_tasks
            WHERE order_item_id IS NOT NULL
            UNION ALL
            SELECT gen_random_uuid(), 'production', id, order_item_id, 0
            FROM production_tasks
            WHERE order_item_id IS NOT NULL
            UNION ALL
            SELECT gen_random_uuid(), 'installation', id, order_item_id, 0
            FROM installation_tasks
            WHERE order_item_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_order_item_link_item",
        table_name="task_order_item_links",
    )
    op.drop_index(
        "ix_task_order_item_link_task",
        table_name="task_order_item_links",
    )
    op.drop_constraint(
        "uq_task_order_item_link",
        "task_order_item_links",
        type_="unique",
    )
    op.drop_constraint(
        "fk_task_order_item_links_order_item_id",
        "task_order_item_links",
        type_="foreignkey",
    )
    op.drop_table("task_order_item_links")
