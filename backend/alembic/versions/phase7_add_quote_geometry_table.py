"""add_quote_geometry_table

Phase 7: 高级几何和板材套料 — 新增几何分析表

Revision ID: phase7_add_quote_geometry
Revises: 83cd02c2a988
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'phase7_add_quote_geometry'
down_revision: Union[str, None] = '83cd02c2a988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("quote_geometry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quote_line_id", UUID(as_uuid=True), sa.ForeignKey("quote_lines.id", ondelete="SET NULL"), nullable=True, unique=True, comment="关联报价明细行"),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("business_documents.id", ondelete="SET NULL"), nullable=True, comment="关联报价 header"),
        # 孔洞与净面积
        sa.Column("net_area_mm2", sa.Numeric(16, 3), nullable=True, comment="净面积（包围盒-孔洞）mm²"),
        sa.Column("hole_area_mm2", sa.Numeric(16, 3), nullable=True, comment="孔洞总面积 mm²"),
        # 曲线信息
        sa.Column("curve_length_mm", sa.Numeric(16, 3), nullable=True, comment="曲线/轮廓长度 mm"),
        sa.Column("is_open_curve", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否开放曲线"),
        # 重叠检测
        sa.Column("overlap_count", sa.Integer(), nullable=True, comment="检测到的重叠对象数"),
        sa.Column("overlap_area_mm2", sa.Numeric(16, 3), nullable=True, comment="重叠区域估计面积 mm²"),
        # 板材套料
        sa.Column("sheet_count", sa.Integer(), nullable=True, comment="预估需用板材张数"),
        sa.Column("sheet_utilization_pct", sa.Numeric(6, 3), nullable=True, comment="板材利用率（%）"),
        sa.Column("sheet_width_mm", sa.Numeric(10, 2), nullable=True, comment="使用板材宽 mm"),
        sa.Column("sheet_height_mm", sa.Numeric(10, 2), nullable=True, comment="使用板材高 mm"),
        # 标记
        sa.Column("is_estimated", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="是否为估算值"),
        # 完整数据
        sa.Column("nesting_json", JSONB(), nullable=True, comment="排版布局结果"),
        sa.Column("analysis_json", JSONB(), nullable=True, comment="完整几何分析明细"),
        # 时间戳
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_quote_geometry_quote_line_id", "quote_geometry", ["quote_line_id"], unique=True)
    op.create_index("ix_quote_geometry_quote_id", "quote_geometry", ["quote_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_geometry_quote_id")
    op.drop_index("ix_quote_geometry_quote_line_id")
    op.drop_table("quote_geometry")
