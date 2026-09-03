"""Link external tasks to order items and preserve fractional quantities.

The relationship is optional for compatibility with historical order-level and
quote-level external tasks.  Existing non-null links are validated before the
foreign key is created; no historical link is inferred or rewritten.
"""

from alembic import context, op
import sqlalchemy as sa


revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        invalid_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM outsource_tasks AS task
                LEFT JOIN business_document_items AS item
                  ON item.id = task.order_item_id
                WHERE task.order_item_id IS NOT NULL
                  AND item.id IS NULL
                """
            )
        ).scalar_one()
        if invalid_count:
            raise RuntimeError(
                f"outsource_tasks.order_item_id contains {invalid_count} invalid values"
            )

    op.alter_column(
        "outsource_tasks",
        "quantity",
        existing_type=sa.Integer(),
        type_=sa.Numeric(14, 3),
        existing_nullable=False,
        postgresql_using="quantity::numeric",
    )
    op.create_foreign_key(
        "fk_outsource_tasks_order_item_id",
        "outsource_tasks",
        "business_document_items",
        ["order_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_outsource_order_item",
        "outsource_tasks",
        ["order_item_id"],
    )


def downgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        fractional_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM outsource_tasks
                WHERE quantity != trunc(quantity)
                """
            )
        ).scalar_one()
        if fractional_count:
            raise RuntimeError(
                "Cannot downgrade outsource_tasks.quantity while fractional quantities exist"
            )

    op.drop_index("ix_outsource_order_item", table_name="outsource_tasks")
    op.drop_constraint(
        "fk_outsource_tasks_order_item_id",
        "outsource_tasks",
        type_="foreignkey",
    )
    op.alter_column(
        "outsource_tasks",
        "quantity",
        existing_type=sa.Numeric(14, 3),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="quantity::integer",
    )
