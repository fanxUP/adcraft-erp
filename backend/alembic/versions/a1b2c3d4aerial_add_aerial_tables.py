"""add aerial work platform tables

Revision ID: a1b2c3d4e5f6
Revises: w1x2y3z4
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4aerial'
down_revision = 'w1x2y3z4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── aerial_drivers ──
    op.create_table(
        'aerial_drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_name', sa.String(64), nullable=False),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('license_no', sa.String(64), nullable=True),
        sa.Column('license_type', sa.String(32), nullable=True),
        sa.Column('license_expire_date', sa.DateTime, nullable=True),
        sa.Column('is_external', sa.Boolean, server_default='false', nullable=False),
        sa.Column('status', sa.String(32), server_default='active', nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── aerial_vehicles ──
    op.create_table(
        'aerial_vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plate_number', sa.String(32), unique=True, nullable=False),
        sa.Column('vehicle_name', sa.String(128), nullable=False),
        sa.Column('brand_model', sa.String(128), nullable=True),
        sa.Column('max_working_height', sa.String(32), nullable=True),
        sa.Column('platform_capacity', sa.String(32), nullable=True),
        sa.Column('purchase_date', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(32), server_default='available', nullable=False),
        sa.Column('default_driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_drivers.id'), nullable=True),
        sa.Column('insurance_expire_date', sa.DateTime, nullable=True),
        sa.Column('inspection_expire_date', sa.DateTime, nullable=True),
        sa.Column('maintenance_due_date', sa.DateTime, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── aerial_daily_ledgers ──
    op.create_table(
        'aerial_daily_ledgers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_no', sa.String(64), unique=True, nullable=False),
        sa.Column('work_date', sa.DateTime, nullable=False),
        sa.Column('aerial_vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_vehicles.id'), nullable=False),
        sa.Column('plate_number', sa.String(32), nullable=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_drivers.id'), nullable=False),
        sa.Column('assistant_names', sa.Text, nullable=True),
        sa.Column('customer_name', sa.String(128), nullable=True),
        sa.Column('contact_name', sa.String(64), nullable=True),
        sa.Column('contact_phone', sa.String(32), nullable=True),
        sa.Column('related_order_no', sa.String(64), nullable=True),
        sa.Column('related_task_no', sa.String(64), nullable=True),
        sa.Column('work_location', sa.String(256), nullable=False),
        sa.Column('work_type', sa.String(64), nullable=True),
        sa.Column('work_content', sa.Text, nullable=True),
        sa.Column('planned_start_time', sa.DateTime, nullable=True),
        sa.Column('planned_end_time', sa.DateTime, nullable=True),
        sa.Column('actual_start_time', sa.DateTime, nullable=True),
        sa.Column('actual_end_time', sa.DateTime, nullable=True),
        sa.Column('billing_method', sa.String(32), server_default='trip', nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), server_default='1', nullable=False),
        sa.Column('receivable_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('discount_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('final_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('received_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('unpaid_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('settlement_type', sa.String(32), server_default='separate', nullable=False),
        sa.Column('payment_status', sa.String(32), server_default='unpaid', nullable=False),
        sa.Column('payment_method', sa.String(32), nullable=True),
        sa.Column('payment_time', sa.DateTime, nullable=True),
        sa.Column('invoice_required', sa.Boolean, server_default='false', nullable=False),
        sa.Column('invoice_status', sa.String(32), nullable=True),
        sa.Column('start_mileage', sa.Numeric(10, 1), nullable=True),
        sa.Column('end_mileage', sa.Numeric(10, 1), nullable=True),
        sa.Column('distance_km', sa.Numeric(10, 1), nullable=True),
        sa.Column('driver_wage_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('reimbursement_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('vehicle_direct_cost', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('gross_profit', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('estimated_profit', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('abnormal_flag', sa.Boolean, server_default='false', nullable=False),
        sa.Column('abnormal_description', sa.Text, nullable=True),
        sa.Column('status', sa.String(32), server_default='draft', nullable=False),
        sa.Column('audit_status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('voided_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('voided_at', sa.DateTime, nullable=True),
        sa.Column('void_reason', sa.Text, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_aerial_ledger_work_date', 'aerial_daily_ledgers', ['work_date'])
    op.create_index('ix_aerial_ledger_driver_id', 'aerial_daily_ledgers', ['driver_id'])
    op.create_index('ix_aerial_ledger_customer_name', 'aerial_daily_ledgers', ['customer_name'])
    op.create_index('ix_aerial_ledger_status', 'aerial_daily_ledgers', ['status'])
    op.create_index('ix_aerial_ledger_payment_status', 'aerial_daily_ledgers', ['payment_status'])

    # ── aerial_driver_expenses ──
    op.create_table(
        'aerial_driver_expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=False),
        sa.Column('expense_date', sa.DateTime, nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_drivers.id'), nullable=False),
        sa.Column('expense_type', sa.String(32), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_method', sa.String(32), nullable=True),
        sa.Column('paid_by_driver', sa.Boolean, server_default='true', nullable=False),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('review_status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('reimbursement_status', sa.String(32), server_default='unpaid', nullable=False),
        sa.Column('reimbursed_at', sa.DateTime, nullable=True),
        sa.Column('reimbursed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_aerial_expense_driver_id', 'aerial_driver_expenses', ['driver_id'])
    op.create_index('ix_aerial_expense_expense_date', 'aerial_driver_expenses', ['expense_date'])

    # ── aerial_driver_wages ──
    op.create_table(
        'aerial_driver_wages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=True),
        sa.Column('wage_month', sa.String(7), nullable=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_drivers.id'), nullable=False),
        sa.Column('wage_type', sa.String(32), server_default='daily', nullable=False),
        sa.Column('base_wage', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('trip_wage', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('hourly_wage', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('commission_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('allowance_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('deduction_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('final_wage_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('payment_status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('paid_at', sa.DateTime, nullable=True),
        sa.Column('paid_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_aerial_wage_driver_id', 'aerial_driver_wages', ['driver_id'])
    op.create_index('ix_aerial_wage_wage_month', 'aerial_driver_wages', ['wage_month'])

    # ── aerial_vehicle_costs ──
    op.create_table(
        'aerial_vehicle_costs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('aerial_vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_vehicles.id'), nullable=False),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=True),
        sa.Column('cost_date', sa.DateTime, nullable=False),
        sa.Column('cost_type', sa.String(32), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('handler_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_method', sa.String(32), nullable=True),
        sa.Column('is_driver_advance', sa.Boolean, server_default='false', nullable=False),
        sa.Column('need_reimbursement', sa.Boolean, server_default='false', nullable=False),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('allocation_type', sa.String(32), server_default='none', nullable=False),
        sa.Column('allocation_month', sa.String(7), nullable=True),
        sa.Column('review_status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_aerial_vcost_vehicle_id', 'aerial_vehicle_costs', ['aerial_vehicle_id'])
    op.create_index('ix_aerial_vcost_cost_date', 'aerial_vehicle_costs', ['cost_date'])
    op.create_index('ix_aerial_vcost_cost_type', 'aerial_vehicle_costs', ['cost_type'])

    # ── aerial_safety_checks ──
    op.create_table(
        'aerial_safety_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=False),
        sa.Column('check_type', sa.String(32), nullable=False),
        sa.Column('checker_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vehicle_appearance_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('tire_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('brake_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('light_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('hydraulic_system_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('outriggers_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('platform_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('safety_belt_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('warning_equipment_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('extinguisher_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('documents_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('weather_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('site_risk_ok', sa.Boolean, server_default='true', nullable=False),
        sa.Column('issue_description', sa.Text, nullable=True),
        sa.Column('photo_urls', sa.Text, nullable=True),
        sa.Column('check_result', sa.String(32), server_default='passed', nullable=False),
        sa.Column('checked_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── aerial_ledger_attachments ──
    op.create_table(
        'aerial_ledger_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=False),
        sa.Column('attachment_type', sa.String(32), server_default='other', nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(256), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
    )

    # ── aerial_ledger_audit_logs ──
    op.create_table(
        'aerial_ledger_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('aerial_daily_ledgers.id'), nullable=True),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('source', sa.String(32), server_default='erp', nullable=False),
        sa.Column('target_type', sa.String(64), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('before_json', sa.Text, nullable=True),
        sa.Column('after_json', sa.Text, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('aerial_ledger_audit_logs')
    op.drop_table('aerial_ledger_attachments')
    op.drop_table('aerial_safety_checks')
    op.drop_table('aerial_vehicle_costs')
    op.drop_table('aerial_driver_wages')
    op.drop_table('aerial_driver_expenses')
    op.drop_table('aerial_daily_ledgers')
    op.drop_table('aerial_vehicles')
    op.drop_table('aerial_drivers')
