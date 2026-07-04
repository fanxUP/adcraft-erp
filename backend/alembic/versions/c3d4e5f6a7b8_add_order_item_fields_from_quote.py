"""add order item fields from quote

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("length_unit", sa.String(16), nullable=True, server_default="m"))
    op.add_column("order_items", sa.Column("width_unit", sa.String(16), nullable=True, server_default="m"))
    op.add_column("order_items", sa.Column("height_unit", sa.String(16), nullable=True, server_default="m"))
    op.add_column("order_items", sa.Column("use_area", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("order_items", sa.Column("quantity_mode", sa.String(16), nullable=False, server_default="piece"))
    op.add_column("order_items", sa.Column("area", sa.Numeric(14, 3), nullable=True))
    op.add_column("order_items", sa.Column("process_fee", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("installation_fee", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("design_fee", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("transport_fee", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("other_fee", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("group_name", sa.String(255), nullable=True))
    op.add_column("order_items", sa.Column("material_process", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("order_items", "material_process")
    op.drop_column("order_items", "group_name")
    op.drop_column("order_items", "sort_order")
    op.drop_column("order_items", "other_fee")
    op.drop_column("order_items", "transport_fee")
    op.drop_column("order_items", "design_fee")
    op.drop_column("order_items", "installation_fee")
    op.drop_column("order_items", "process_fee")
    op.drop_column("order_items", "area")
    op.drop_column("order_items", "quantity_mode")
    op.drop_column("order_items", "use_area")
    op.drop_column("order_items", "height_unit")
    op.drop_column("order_items", "width_unit")
    op.drop_column("order_items", "length_unit")
