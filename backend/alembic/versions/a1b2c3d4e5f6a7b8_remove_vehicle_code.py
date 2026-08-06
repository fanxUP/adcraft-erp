"""remove vehicle_code column from vehicles

Revision ID: a1b2c3d4e5f6a7b8
Revises: b9c8d7e6f5a4b3c2
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6a7b8'
down_revision = 'b9c8d7e6f5a4b3c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 车辆编号列与其唯一约束一并删除
    op.drop_constraint('vehicles_vehicle_code_key', 'vehicles', type_='unique')
    op.drop_column('vehicles', 'vehicle_code')


def downgrade() -> None:
    # 恢复列（server_default 保证对已有行可回填），并重建唯一约束
    op.add_column(
        'vehicles',
        sa.Column('vehicle_code', sa.String(64), nullable=False, server_default=''),
    )
    op.create_unique_constraint('vehicles_vehicle_code_key', 'vehicles', ['vehicle_code'])
