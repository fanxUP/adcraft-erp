"""Bind order-stage materials to the order item they document.

The column is intentionally nullable.  Existing order-level materials and
legacy rows remain visible under the unassociated bucket; only materials
uploaded from the per-item completion flow receive an item id.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "osa02_attachment_order_item"
down_revision: Union[str, None] = "oid01_item_delete_consistency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column(
            "order_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_attachments_order_item_id_business_document_items",
        "attachments",
        "business_document_items",
        ["order_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_attachments_order_stage_item_created_at",
        "attachments",
        ["order_id", "stage", "order_item_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    linked_count = bind.execute(
        sa.text("SELECT count(*) FROM attachments WHERE order_item_id IS NOT NULL")
    ).scalar_one()
    if linked_count:
        raise RuntimeError(
            "不能回滚订单明细资料归属字段：attachments 中仍有已绑定明细的资料；"
            "请先完成应用版本回退和附件元数据迁移方案"
        )

    op.drop_index("ix_attachments_order_stage_item_created_at", table_name="attachments")
    op.drop_constraint(
        "fk_attachments_order_item_id_business_document_items",
        "attachments",
        type_="foreignkey",
    )
    op.drop_column("attachments", "order_item_id")
