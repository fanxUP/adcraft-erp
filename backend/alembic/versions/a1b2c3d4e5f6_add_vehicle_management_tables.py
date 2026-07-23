"""add vehicle management tables

Revision ID: a1b2c3d4e5f6
Revises: feedc0de0001
Create Date: 2026-07-23 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'feedc0de0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 车辆档案 ──
    op.create_table(
        'vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vehicle_code', sa.String(64), unique=True, nullable=False, comment='车辆编号'),
        sa.Column('plate_number', sa.String(32), unique=True, nullable=False, comment='车牌号'),
        sa.Column('vehicle_name', sa.String(128), nullable=False, comment='车辆名称'),
        sa.Column('vehicle_type', sa.String(32), nullable=False, comment='车辆类型'),
        sa.Column('brand_model', sa.String(128), nullable=True, comment='品牌型号'),
        sa.Column('color', sa.String(32), nullable=True, comment='颜色'),
        sa.Column('purchase_date', sa.DateTime(), nullable=True, comment='购买日期'),
        sa.Column('status', sa.String(32), nullable=False, server_default='available', comment='状态'),
        sa.Column('department', sa.String(64), nullable=True, comment='所属部门'),
        sa.Column('default_driver_id', postgresql.UUID(as_uuid=True), nullable=True, comment='默认司机'),
        sa.Column('load_capacity', sa.String(64), nullable=True, comment='载重信息'),
        sa.Column('seats', sa.Integer(), nullable=True, comment='座位数'),
        sa.Column('vehicle_photo_url', sa.String(500), nullable=True, comment='车辆照片'),
        sa.Column('license_photo_url', sa.String(500), nullable=True, comment='行驶证照片'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_vehicles_status', 'vehicles', ['status'])
    op.create_index('ix_vehicles_plate_number', 'vehicles', ['plate_number'])

    # ── 司机档案 ──
    op.create_table(
        'vehicle_drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='绑定员工'),
        sa.Column('driver_name', sa.String(64), nullable=False, comment='司机姓名'),
        sa.Column('phone', sa.String(32), nullable=True, comment='手机号'),
        sa.Column('license_no', sa.String(64), nullable=True, comment='驾驶证号'),
        sa.Column('license_type', sa.String(32), nullable=True, comment='驾驶证类型'),
        sa.Column('license_expire_date', sa.DateTime(), nullable=True, comment='驾驶证到期日'),
        sa.Column('is_external', sa.Boolean(), nullable=False, server_default='false', comment='是否外协司机'),
        sa.Column('status', sa.String(32), nullable=False, server_default='active', comment='状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_vehicle_drivers_employee_id', 'vehicle_drivers', ['employee_id'])
    op.create_index('ix_vehicle_drivers_status', 'vehicle_drivers', ['status'])

    # Add FK for vehicles.default_driver_id after vehicle_drivers is created
    op.create_foreign_key('fk_vehicles_default_driver_id', 'vehicles', 'vehicle_drivers', ['default_driver_id'], ['id'])

    # ── 用车申请 ──
    op.create_table(
        'vehicle_use_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_no', sa.String(64), unique=True, nullable=False, comment='申请单号'),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, comment='申请人'),
        sa.Column('reason', sa.String(32), nullable=False, comment='用车原因'),
        sa.Column('related_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True, comment='关联客户'),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True, comment='关联订单'),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True, comment='关联安装任务'),
        sa.Column('start_time', sa.DateTime(), nullable=True, comment='出发时间'),
        sa.Column('expected_return_time', sa.DateTime(), nullable=True, comment='预计返回时间'),
        sa.Column('destination', sa.String(255), nullable=True, comment='目的地'),
        sa.Column('need_driver', sa.Boolean(), nullable=False, server_default='true', comment='是否需要司机'),
        sa.Column('need_cargo', sa.Boolean(), nullable=False, server_default='false', comment='是否需要装货'),
        sa.Column('cargo_description', sa.Text(), nullable=True, comment='货物说明'),
        sa.Column('estimated_distance_km', sa.Numeric(10, 2), nullable=True, comment='预计里程(km)'),
        sa.Column('status', sa.String(32), nullable=False, server_default='draft', comment='状态'),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='审批人'),
        sa.Column('approved_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('reject_reason', sa.Text(), nullable=True, comment='驳回原因'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_use_requests_requester_id', 'vehicle_use_requests', ['requester_id'])
    op.create_index('ix_vehicle_use_requests_status', 'vehicle_use_requests', ['status'])

    # ── 派车单 ──
    op.create_table(
        'vehicle_dispatches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('dispatch_no', sa.String(64), unique=True, nullable=False, comment='派车单号'),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_use_requests.id'), nullable=True, comment='用车申请'),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True, comment='司机'),
        sa.Column('related_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True, comment='关联客户'),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True, comment='关联订单'),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True, comment='关联安装任务'),
        sa.Column('start_location', sa.String(255), nullable=True, comment='出发地点'),
        sa.Column('destination', sa.String(255), nullable=True, comment='目的地'),
        sa.Column('planned_start_time', sa.DateTime(), nullable=True, comment='计划出发时间'),
        sa.Column('planned_return_time', sa.DateTime(), nullable=True, comment='计划返回时间'),
        sa.Column('actual_start_time', sa.DateTime(), nullable=True, comment='实际出发时间'),
        sa.Column('actual_return_time', sa.DateTime(), nullable=True, comment='实际返回时间'),
        sa.Column('start_mileage', sa.Numeric(12, 1), nullable=True, comment='出车里程(km)'),
        sa.Column('end_mileage', sa.Numeric(12, 1), nullable=True, comment='收车里程(km)'),
        sa.Column('actual_distance_km', sa.Numeric(10, 2), nullable=True, comment='实际行驶里程(km)'),
        sa.Column('status', sa.String(32), nullable=False, server_default='assigned', comment='状态'),
        sa.Column('abnormal_flag', sa.Boolean(), nullable=False, server_default='false', comment='是否有异常'),
        sa.Column('abnormal_description', sa.Text(), nullable=True, comment='异常说明'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_dispatches_vehicle_id_planned', 'vehicle_dispatches', ['vehicle_id', 'planned_start_time', 'planned_return_time'])
    op.create_index('ix_vehicle_dispatches_driver_id', 'vehicle_dispatches', ['driver_id'])
    op.create_index('ix_vehicle_dispatches_related_order_id', 'vehicle_dispatches', ['related_order_id'])
    op.create_index('ix_vehicle_dispatches_status', 'vehicle_dispatches', ['status'])

    # ── 出车/收车台账 ──
    op.create_table(
        'vehicle_trip_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_no', sa.String(64), unique=True, nullable=False, comment='台账编号'),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=False, comment='派车单'),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True, comment='司机'),
        sa.Column('trip_date', sa.DateTime(), nullable=True, comment='出车日期'),
        sa.Column('start_time', sa.DateTime(), nullable=True, comment='出车时间'),
        sa.Column('return_time', sa.DateTime(), nullable=True, comment='收车时间'),
        sa.Column('start_mileage', sa.Numeric(12, 1), nullable=True, comment='出车里程'),
        sa.Column('end_mileage', sa.Numeric(12, 1), nullable=True, comment='收车里程'),
        sa.Column('distance_km', sa.Numeric(10, 2), nullable=True, comment='实际公里数'),
        sa.Column('start_photo_url', sa.String(500), nullable=True, comment='出车照片'),
        sa.Column('return_photo_url', sa.String(500), nullable=True, comment='收车照片'),
        sa.Column('start_remark', sa.Text(), nullable=True, comment='出车备注'),
        sa.Column('return_remark', sa.Text(), nullable=True, comment='收车备注'),
        sa.Column('abnormal_flag', sa.Boolean(), nullable=False, server_default='false', comment='是否有异常'),
        sa.Column('abnormal_description', sa.Text(), nullable=True, comment='异常说明'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_trip_records_vehicle_id_trip_date', 'vehicle_trip_records', ['vehicle_id', 'trip_date'])
    op.create_index('ix_vehicle_trip_records_dispatch_id', 'vehicle_trip_records', ['dispatch_id'])

    # ── 油费记录 ──
    op.create_table(
        'vehicle_fuel_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True, comment='司机'),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True, comment='派车单'),
        sa.Column('fuel_time', sa.DateTime(), nullable=True, comment='加油时间'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='金额'),
        sa.Column('liters', sa.Numeric(10, 2), nullable=True, comment='升数'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=True, comment='单价'),
        sa.Column('gas_station', sa.String(128), nullable=True, comment='加油站'),
        sa.Column('mileage', sa.Numeric(12, 1), nullable=True, comment='当前里程'),
        sa.Column('payment_method', sa.String(32), nullable=True, comment='支付方式'),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='付款人'),
        sa.Column('is_driver_advance', sa.Boolean(), nullable=False, server_default='false', comment='是否司机垫付'),
        sa.Column('receipt_url', sa.String(500), nullable=True, comment='票据照片'),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending_review', comment='审核状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_fuel_records_vehicle_id_fuel_time', 'vehicle_fuel_records', ['vehicle_id', 'fuel_time'])
    op.create_index('ix_vehicle_fuel_records_status', 'vehicle_fuel_records', ['status'])

    # ── 维修保养记录 ──
    op.create_table(
        'vehicle_maintenance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('maintenance_type', sa.String(32), nullable=False, comment='类型'),
        sa.Column('maintenance_date', sa.DateTime(), nullable=True, comment='维修日期'),
        sa.Column('maintenance_item', sa.String(255), nullable=True, comment='维修项目'),
        sa.Column('repair_shop', sa.String(128), nullable=True, comment='维修厂'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='金额'),
        sa.Column('mileage', sa.Numeric(12, 1), nullable=True, comment='当前里程'),
        sa.Column('next_maintenance_mileage', sa.Numeric(12, 1), nullable=True, comment='下次保养里程'),
        sa.Column('next_maintenance_date', sa.DateTime(), nullable=True, comment='下次保养日期'),
        sa.Column('handler_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='经办人'),
        sa.Column('invoice_url', sa.String(500), nullable=True, comment='发票照片'),
        sa.Column('before_photo_url', sa.String(500), nullable=True, comment='维修前照片'),
        sa.Column('after_photo_url', sa.String(500), nullable=True, comment='维修后照片'),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending_review', comment='审核状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_maintenance_records_vehicle_id', 'vehicle_maintenance_records', ['vehicle_id'])
    op.create_index('ix_vehicle_maintenance_records_status', 'vehicle_maintenance_records', ['status'])

    # ── 保险/年检/证件 ──
    op.create_table(
        'vehicle_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True, comment='司机'),
        sa.Column('certificate_type', sa.String(32), nullable=False, comment='证件类型'),
        sa.Column('certificate_no', sa.String(128), nullable=True, comment='证件编号'),
        sa.Column('start_date', sa.DateTime(), nullable=True, comment='开始日期'),
        sa.Column('expire_date', sa.DateTime(), nullable=True, comment='到期日期'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='金额'),
        sa.Column('file_url', sa.String(500), nullable=True, comment='附件'),
        sa.Column('reminder_days', sa.Integer(), nullable=False, server_default='30', comment='提前提醒天数'),
        sa.Column('status', sa.String(32), nullable=False, server_default='active', comment='状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_certificates_vehicle_id_expire_date', 'vehicle_certificates', ['vehicle_id', 'expire_date'])
    op.create_index('ix_vehicle_certificates_certificate_type', 'vehicle_certificates', ['certificate_type'])

    # ── 违章/事故/异常 ──
    op.create_table(
        'vehicle_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_drivers.id'), nullable=True, comment='司机'),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True, comment='派车单'),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True, comment='关联订单'),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True, comment='关联安装任务'),
        sa.Column('incident_type', sa.String(32), nullable=False, comment='事件类型'),
        sa.Column('incident_time', sa.DateTime(), nullable=True, comment='发生时间'),
        sa.Column('location', sa.String(255), nullable=True, comment='发生地点'),
        sa.Column('description', sa.Text(), nullable=True, comment='事件描述'),
        sa.Column('fine_amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='罚款金额'),
        sa.Column('points_deducted', sa.Integer(), nullable=False, server_default='0', comment='扣分'),
        sa.Column('repair_amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='维修金额'),
        sa.Column('responsible_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True, comment='责任人'),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending', comment='处理状态'),
        sa.Column('resolution', sa.Text(), nullable=True, comment='处理结果'),
        sa.Column('evidence_url', sa.String(500), nullable=True, comment='证据照片'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_vehicle_incidents_vehicle_id', 'vehicle_incidents', ['vehicle_id'])
    op.create_index('ix_vehicle_incidents_status', 'vehicle_incidents', ['status'])
    op.create_index('ix_vehicle_incidents_incident_type', 'vehicle_incidents', ['incident_type'])

    # ── 费用分摊 ──
    op.create_table(
        'vehicle_cost_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_type', sa.String(32), nullable=False, comment='来源类型'),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False, comment='来源记录ID'),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=False, comment='车辆'),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicle_dispatches.id'), nullable=True, comment='派车单'),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=True, comment='关联订单'),
        sa.Column('related_install_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('installation_tasks.id'), nullable=True, comment='关联安装任务'),
        sa.Column('cost_type', sa.String(32), nullable=False, comment='费用类型'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0', comment='金额'),
        sa.Column('allocation_method', sa.String(32), nullable=False, server_default='manual', comment='分摊方式'),
        sa.Column('allocation_date', sa.DateTime(), nullable=True, comment='分摊日期'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
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
    op.drop_constraint('fk_vehicles_default_driver_id', 'vehicles', type_='foreignkey')
    op.drop_table('vehicle_drivers')
    op.drop_table('vehicles')
