"""add aerial attendance records table

Revision ID: b7c8d9e0f1a2b3c4
Revises: 63a384fdefbf
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b7c8d9e0f1a2b3c4'
down_revision = '63a384fdefbf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── aerial_attendance_records（高空作业考勤，独立于出车台账） ──
    op.create_table(
        'aerial_attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('att_date', sa.Date, nullable=False),
        sa.Column('target_type', sa.String(16), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_vehicles.id'), nullable=True),
        sa.Column('personnel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_personnel.id'), nullable=True),
        sa.Column('status', sa.String(16), server_default='present', nullable=False),
        sa.Column('check_in_time', sa.DateTime, nullable=True),
        sa.Column('check_out_time', sa.DateTime, nullable=True),
        sa.Column('overtime_hours', sa.Numeric(5, 1), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('source', sa.String(16), server_default='manual_input', nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    # 同一车辆/人员同一天仅一条（部分唯一索引）
    op.create_index(
        'uq_aerial_att_vehicle_day', 'aerial_attendance_records',
        ['att_date', 'vehicle_id'], unique=True,
        postgresql_where=sa.text("target_type = 'vehicle'"),
    )
    op.create_index(
        'uq_aerial_att_personnel_day', 'aerial_attendance_records',
        ['att_date', 'personnel_id'], unique=True,
        postgresql_where=sa.text("target_type = 'personnel'"),
    )


def downgrade() -> None:
    op.drop_index('uq_aerial_att_personnel_day', table_name='aerial_attendance_records')
    op.drop_index('uq_aerial_att_vehicle_day', table_name='aerial_attendance_records')
    op.drop_table('aerial_attendance_records')
