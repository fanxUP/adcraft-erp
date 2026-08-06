"""add company vehicle attachments table

Revision ID: e2f3a4b5c6d7e8f9
Revises: c5d6e7f8a9b0c1d2
Create Date: 2026-08-06 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7e8f9'
down_revision: Union[str, None] = 'c5d6e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 公司车辆档案附件（照搬高空车 aerial_vehicle_attachments）
    op.create_table(
        'vehicle_attachments',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('vehicle_id', sa.UUID(), sa.ForeignKey('vehicles.id'), nullable=False, comment='关联车辆'),
        sa.Column('attachment_type', sa.String(32), server_default='other', nullable=False, comment='附件类型: license/registration/insurance/inspection/maintenance/other'),
        sa.Column('file_url', sa.String(500), nullable=False, comment='文件URL'),
        sa.Column('file_name', sa.String(256), nullable=True, comment='文件名'),
        sa.Column('uploaded_by', sa.UUID(), nullable=True, comment='上传人'),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='上传时间'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
    )
    op.create_index('ix_vehicle_attachments_vehicle_id', 'vehicle_attachments', ['vehicle_id'])


def downgrade() -> None:
    op.drop_index('ix_vehicle_attachments_vehicle_id', table_name='vehicle_attachments')
    op.drop_table('vehicle_attachments')
