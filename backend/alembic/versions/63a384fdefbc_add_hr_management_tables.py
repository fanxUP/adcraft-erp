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
