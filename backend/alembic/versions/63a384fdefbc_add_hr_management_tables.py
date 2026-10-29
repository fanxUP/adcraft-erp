"""add_hr_management_tables

Revision ID: 63a384fdefbc
Revises: e0f1a2b3c4d5
Create Date: 2026-07-30 11:59:48.868990
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '63a384fdefbc'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Early native installs created these three tables outside Alembic. Keep
    # their historical structure here (not today's ORM metadata), so later
    # revisions can replay normally and existing installations are untouched.
    tables = sa.inspect(op.get_bind()).get_table_names()
    if 'employees' not in tables:
        op.create_table('employees',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('employee_no', sa.String(32), nullable=False, unique=True),
            sa.Column('name', sa.String(64), nullable=False),
            *[sa.Column(name, sa.String(size), nullable=True) for name, size in (
                ('phone', 32), ('gender', 8), ('department', 32), ('position', 64),
                ('employment_type', 16), ('id_card', 32), ('education', 32),
                ('emergency_contact', 32), ('emergency_phone', 32),
                ('bank_name', 128), ('bank_account', 64), ('address', 500),
            )],
            sa.Column('birth_date', sa.Date()), sa.Column('hire_date', sa.Date()),
            sa.Column('resignation_date', sa.Date()),
            sa.Column('employment_status', sa.String(16), nullable=False, server_default='active'),
            sa.Column('base_salary', sa.Numeric(14, 2)),
            sa.Column('skills', postgresql.JSONB()),
            sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id')),
            sa.Column('remark', sa.Text()),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('deleted_at', sa.DateTime()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if 'attendance_rules' not in tables:
        op.create_table('attendance_rules',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('name', sa.String(64), nullable=False),
            sa.Column('department', sa.String(32)),
            sa.Column('check_in_time', sa.Time(), nullable=False),
            sa.Column('check_out_time', sa.Time(), nullable=False),
            sa.Column('work_days', postgresql.JSONB()),
            sa.Column('late_threshold', sa.Integer()),
            sa.Column('early_leave_threshold', sa.Integer()),
            sa.Column('overtime_rate', sa.Numeric(3, 1)),
            sa.Column('is_active', sa.Boolean()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if 'attendance_records' not in tables:
        op.create_table('attendance_records',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('employee_id', sa.UUID(), sa.ForeignKey('employees.id'), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('check_in_time', sa.DateTime()), sa.Column('check_out_time', sa.DateTime()),
            sa.Column('check_in_status', sa.String(16)), sa.Column('check_out_status', sa.String(16)),
            sa.Column('source', sa.String(16)), sa.Column('remark', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    # departments
    op.create_table('departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(32), nullable=False),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(None, 'departments', ['code'])

    # salary_records
    op.create_table('salary_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('month', sa.String(7), nullable=False),
        sa.Column('base_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('overtime_pay', sa.Numeric(14, 2), nullable=True),
        sa.Column('bonus', sa.Numeric(14, 2), nullable=True),
        sa.Column('commission', sa.Numeric(14, 2), nullable=True),
        sa.Column('subsidy', sa.Numeric(14, 2), nullable=True),
        sa.Column('deduction', sa.Numeric(14, 2), nullable=True),
        sa.Column('net_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('payment_status', sa.String(16), default='pending'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # employment_histories
    op.create_table('employment_histories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('change_date', sa.Date, nullable=False),
        sa.Column('change_type', sa.String(16), nullable=False),
        sa.Column('previous_department', sa.String(32), nullable=True),
        sa.Column('new_department', sa.String(32), nullable=True),
        sa.Column('previous_position', sa.String(64), nullable=True),
        sa.Column('new_position', sa.String(64), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # leave_requests
    op.create_table('leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('leave_type', sa.String(16), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('duration_days', sa.Numeric(5, 1), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('status', sa.String(16), default='pending'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('leave_requests')
    op.drop_table('employment_histories')
    op.drop_table('salary_records')
    op.drop_table('departments')
