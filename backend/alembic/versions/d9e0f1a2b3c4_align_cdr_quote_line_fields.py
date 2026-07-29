"""统一智能报价与常规报价明细字段，并迁移历史报价尺寸。

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = (
        sa.Column("material_process", sa.String(length=500), nullable=True),
        sa.Column("width", sa.Numeric(12, 3), nullable=True),
        sa.Column("width_unit", sa.String(length=16), nullable=True),
        sa.Column("height", sa.Numeric(12, 3), nullable=True),
        sa.Column("height_unit", sa.String(length=16), nullable=True),
        sa.Column("use_area", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("process_fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("installation_fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("design_fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("transport_fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("other_fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("group_name", sa.String(length=255), nullable=True),
    )
    for column in columns:
        op.add_column("quote_lines", column)

    op.execute(
        """
        UPDATE quote_lines
        SET width = width_mm,
            width_unit = CASE WHEN width_mm IS NULL THEN NULL ELSE 'mm' END,
            height = height_mm,
            height_unit = CASE WHEN height_mm IS NULL THEN NULL ELSE 'mm' END
        """
    )

    # 历史常规报价：原长、宽迁移为新宽、高，旧高按业务要求清除。
    op.execute(
        """
        UPDATE business_document_items AS item
        SET height = item.width,
            height_unit = item.width_unit,
            width = item.length,
            width_unit = item.length_unit,
            length = NULL,
            length_unit = NULL
        FROM business_documents AS document
        WHERE item.document_id = document.id
          AND document.doc_type = 'quote'
        """
    )


def downgrade() -> None:
    # 尽可能反向恢复迁移后的宽、高；按需求删除的旧高无法恢复。
    op.execute(
        """
        UPDATE business_document_items AS item
        SET length = item.width,
            length_unit = item.width_unit,
            width = item.height,
            width_unit = item.height_unit,
            height = NULL,
            height_unit = NULL
        FROM business_documents AS document
        WHERE item.document_id = document.id
          AND document.doc_type = 'quote'
        """
    )

    for name in (
        "group_name",
        "sort_order",
        "image_url",
        "remark",
        "other_fee",
        "transport_fee",
        "design_fee",
        "installation_fee",
        "process_fee",
        "use_area",
        "height_unit",
        "height",
        "width_unit",
        "width",
        "material_process",
    ):
        op.drop_column("quote_lines", name)
