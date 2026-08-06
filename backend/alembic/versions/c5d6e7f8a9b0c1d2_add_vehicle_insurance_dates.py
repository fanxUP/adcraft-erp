"""add flat insurance/inspection/maintenance dates to vehicles

Revision ID: c5d6e7f8a9b0c1d2
Revises: a1b2c3d4e5f6a7b8
Create Date: 2026-08-06 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0c1d2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 加扁平日期列（照搬高空车 aerial_vehicles）
    op.add_column('vehicles', sa.Column('insurance_expire_date', sa.DateTime, nullable=True, comment='保险到期日'))
    op.add_column('vehicles', sa.Column('inspection_expire_date', sa.DateTime, nullable=True, comment='年检到期日'))
    op.add_column('vehicles', sa.Column('maintenance_due_date', sa.DateTime, nullable=True, comment='下次保养日期'))

    # 2. 从 vehicle_certificates 回填（保险取交强险+商业险 max、年检取 annual_inspection、保养取 maintenance）
    op.execute('''
        UPDATE vehicles v SET
          insurance_expire_date = (
            SELECT max(vc.expire_date) FROM vehicle_certificates vc
            WHERE vc.vehicle_id = v.id
              AND vc.certificate_type IN ('compulsory_insurance', 'commercial_insurance')
              AND vc.expire_date IS NOT NULL
          ),
          inspection_expire_date = (
            SELECT max(vc.expire_date) FROM vehicle_certificates vc
            WHERE vc.vehicle_id = v.id
              AND vc.certificate_type = 'annual_inspection'
              AND vc.expire_date IS NOT NULL
          ),
          maintenance_due_date = (
            SELECT max(vc.expire_date) FROM vehicle_certificates vc
            WHERE vc.vehicle_id = v.id
              AND vc.certificate_type = 'maintenance'
              AND vc.expire_date IS NOT NULL
          )
    ''')


def downgrade() -> None:
    op.drop_column('vehicles', 'maintenance_due_date')
    op.drop_column('vehicles', 'inspection_expire_date')
    op.drop_column('vehicles', 'insurance_expire_date')
