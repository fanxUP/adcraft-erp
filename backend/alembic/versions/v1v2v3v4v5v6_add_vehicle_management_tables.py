"""add vehicle management tables

Revision ID: v1v2v3v4v5v6
Revises: f0e1d2c3b4a5
Create Date: 2026-07-23 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'v1v2v3v4v5v6'
down_revision: Union[str, None] = 'f0e1d2c3b4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. vehicle_drivers (先建，因为 vehicles 引用它)
    op.create_table(
        'vehicle_drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
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
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    # 2. vehicles
    op.create_table(
        'vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_code', sa.String(64), unique=True, nullable=False),
        sa.Column('plate_number', sa.String(32), unique=True, nullable=False),
        sa.Column('vehicle_name', sa.String(128), nullable=False),
        sa.Column('vehicle_type', sa.String(32), nullable=False),
        sa.Column('brand_model', sa.String(128), nullable=True),
        sa.Column('color', sa.String(32), nullable=True),
        sa.Column('purchase_date', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(32), server_default='available', nullable=False),
        sa.Column('department', sa.String(64), nullable=True),
        sa.Column('default_driver_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('load_capacity', sa.String(64), nullable=True),
        sa.Column('seats', sa.Integer, nullable=True),
        sa.Column('vehicle_photo_url', sa.String(500), nullable=True),
        sa.Column('license_photo_url', sa.String(500), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )
    op.create_foreign_key('fk_vehicles_default_driver_id', 'vehicles', 'vehicle_drivers', ['default_driver_id'], ['id'])
    op.create_index('ix_vehicles_plate_number', 'vehicles', ['plate_number'], unique=True)
    op.create_index('ix_vehicles_status', 'vehicles', ['status'])

    # 3. vehicle_use_requests
    op.create_table(
        'vehicle_use_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_no', sa.String(64), unique=True, nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.String(32), nullable=False),
        sa.Column('related_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True),
        sa.Column('start_time', sa.DateTime, nullable=True),
        sa.Column('expected_return_time', sa.DateTime, nullable=True),
        sa.Column('destination', sa.String(255), nullable=True),
        sa.Column('need_driver', sa.Boolean, server_default='true', nullable=False),
        sa.Column('need_cargo', sa.Boolean, server_default='false', nullable=False),
        sa.Column('cargo_description', sa.Text, nullable=True),
        sa.Column('estimated_distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(32), server_default='draft', nullable=False),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('reject_reason', sa.Text, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_use_requests_requester_id', 'vehicle_use_requests', ['requester_id'])
    op.create_index('ix_vehicle_use_requests_status', 'vehicle_use_requests', ['status'])

    # 4. vehicle_dispatches
    op.create_table(
        'vehicle_dispatches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dispatch_no', sa.String(64), unique=True, nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_use_requests.id'), nullable=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True),
        sa.Column('related_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True),
        sa.Column('start_location', sa.String(255), nullable=True),
        sa.Column('destination', sa.String(255), nullable=True),
        sa.Column('planned_start_time', sa.DateTime, nullable=True),
        sa.Column('planned_return_time', sa.DateTime, nullable=True),
        sa.Column('actual_start_time', sa.DateTime, nullable=True),
        sa.Column('actual_return_time', sa.DateTime, nullable=True),
        sa.Column('start_mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('end_mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('actual_distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(32), server_default='assigned', nullable=False),
        sa.Column('abnormal_flag', sa.Boolean, server_default='false', nullable=False),
        sa.Column('abnormal_description', sa.Text, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_dispatches_vehicle_id_planned', 'vehicle_dispatches', ['vehicle_id', 'planned_start_time', 'planned_return_time'])
    op.create_index('ix_vehicle_dispatches_driver_id', 'vehicle_dispatches', ['driver_id'])
    op.create_index('ix_vehicle_dispatches_related_order_id', 'vehicle_dispatches', ['related_order_id'])
    op.create_index('ix_vehicle_dispatches_status', 'vehicle_dispatches', ['status'])

    # 5. vehicle_trip_records
    op.create_table(
        'vehicle_trip_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trip_no', sa.String(64), unique=True, nullable=False),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True),
        sa.Column('trip_date', sa.DateTime, nullable=True),
        sa.Column('start_time', sa.DateTime, nullable=True),
        sa.Column('return_time', sa.DateTime, nullable=True),
        sa.Column('start_mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('end_mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('start_photo_url', sa.String(500), nullable=True),
        sa.Column('return_photo_url', sa.String(500), nullable=True),
        sa.Column('start_remark', sa.Text, nullable=True),
        sa.Column('return_remark', sa.Text, nullable=True),
        sa.Column('abnormal_flag', sa.Boolean, server_default='false', nullable=False),
        sa.Column('abnormal_description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_trip_records_vehicle_id_trip_date', 'vehicle_trip_records', ['vehicle_id', 'trip_date'])
    op.create_index('ix_vehicle_trip_records_dispatch_id', 'vehicle_trip_records', ['dispatch_id'])

    # 6. vehicle_fuel_records
    op.create_table(
        'vehicle_fuel_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True),
        sa.Column('fuel_time', sa.DateTime, nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('liters', sa.Numeric(10, 2), nullable=True),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('gas_station', sa.String(128), nullable=True),
        sa.Column('mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('payment_method', sa.String(32), nullable=True),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_driver_advance', sa.Boolean, server_default='false', nullable=False),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(32), server_default='pending_review', nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_fuel_records_vehicle_id_fuel_time', 'vehicle_fuel_records', ['vehicle_id', 'fuel_time'])
    op.create_index('ix_vehicle_fuel_records_status', 'vehicle_fuel_records', ['status'])

    # 7. vehicle_maintenance_records
    op.create_table(
        'vehicle_maintenance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('maintenance_type', sa.String(32), nullable=False),
        sa.Column('maintenance_date', sa.DateTime, nullable=True),
        sa.Column('maintenance_item', sa.String(255), nullable=True),
        sa.Column('repair_shop', sa.String(128), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('next_maintenance_mileage', sa.Numeric(12, 1), nullable=True),
        sa.Column('next_maintenance_date', sa.DateTime, nullable=True),
        sa.Column('handler_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('invoice_url', sa.String(500), nullable=True),
        sa.Column('before_photo_url', sa.String(500), nullable=True),
        sa.Column('after_photo_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(32), server_default='pending_review', nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_maintenance_records_vehicle_id', 'vehicle_maintenance_records', ['vehicle_id'])
    op.create_index('ix_vehicle_maintenance_records_status', 'vehicle_maintenance_records', ['status'])

    # 8. vehicle_certificates
    op.create_table(
        'vehicle_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True),
        sa.Column('certificate_type', sa.String(32), nullable=False),
        sa.Column('certificate_no', sa.String(128), nullable=True),
        sa.Column('start_date', sa.DateTime, nullable=True),
        sa.Column('expire_date', sa.DateTime, nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('reminder_days', sa.Integer, server_default='30', nullable=False),
        sa.Column('status', sa.String(32), server_default='active', nullable=False),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_certificates_vehicle_id_expire_date', 'vehicle_certificates', ['vehicle_id', 'expire_date'])
    op.create_index('ix_vehicle_certificates_certificate_type', 'vehicle_certificates', ['certificate_type'])

    # 9. vehicle_incidents
    op.create_table(
        'vehicle_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True),
        sa.Column('incident_type', sa.String(32), nullable=False),
        sa.Column('incident_time', sa.DateTime, nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('fine_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('points_deducted', sa.Integer, server_default='0', nullable=False),
        sa.Column('repair_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('responsible_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(32), server_default='pending', nullable=False),
        sa.Column('resolution', sa.Text, nullable=True),
        sa.Column('evidence_url', sa.String(500), nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_incidents_vehicle_id', 'vehicle_incidents', ['vehicle_id'])
    op.create_index('ix_vehicle_incidents_status', 'vehicle_incidents', ['status'])
    op.create_index('ix_vehicle_incidents_incident_type', 'vehicle_incidents', ['incident_type'])

    # 10. vehicle_cost_allocations
    op.create_table(
        'vehicle_cost_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True),
        sa.Column('cost_type', sa.String(32), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('allocation_method', sa.String(32), server_default='manual', nullable=False),
        sa.Column('allocation_date', sa.DateTime, nullable=True),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vehicle_cost_allocations_vehicle_id', 'vehicle_cost_allocations', ['vehicle_id'])
    op.create_index('ix_vehicle_cost_allocations_related_order_id', 'vehicle_cost_allocations', ['related_order_id'])
    op.create_index('ix_vehicle_cost_allocations_source_type_id', 'vehicle_cost_allocations', ['source_type', 'source_id'])


def downgrade() -> None:
    op.drop_table('vehicle_cost_allocations')
    op.drop_table('vehicle_incidents')
    op.drop_table('vehicle_certificates')
    op.drop_table('vehicle_maintenance_records')
    op.drop_table('vehicle_fuel_records')
    op.drop_table('vehicle_trip_records')
    op.drop_table('vehicle_dispatches')
    op.drop_table('vehicle_use_requests')
    op.drop_table('vehicles')
    op.drop_table('vehicle_drivers')
