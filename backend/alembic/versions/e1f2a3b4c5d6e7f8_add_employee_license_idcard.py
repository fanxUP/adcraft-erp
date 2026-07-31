"""add license info + id card front/back photos to employees

Revision ID: e1f2a3b4c5d6e7f8
Revises: d5e6f7a8b9c0d1e2
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6e7f8'
down_revision = 'd5e6f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 与高空车人员字段对齐：驾驶证信息 + 身份证正反面照片 URL
    op.add_column('employees', sa.Column('license_no', sa.String(64), nullable=True, comment='驾驶证号'))
    op.add_column('employees', sa.Column('license_type', sa.String(32), nullable=True, comment='驾驶证类型'))
    op.add_column('employees', sa.Column('license_expire_date', sa.DateTime(), nullable=True, comment='驾驶证到期日'))
    op.add_column('employees', sa.Column('id_card_front_url', sa.String(500), nullable=True, comment='身份证正面照片'))
    op.add_column('employees', sa.Column('id_card_back_url', sa.String(500), nullable=True, comment='身份证反面照片'))


def downgrade() -> None:
    op.drop_column('employees', 'id_card_back_url')
    op.drop_column('employees', 'id_card_front_url')
    op.drop_column('employees', 'license_expire_date')
    op.drop_column('employees', 'license_type')
    op.drop_column('employees', 'license_no')
