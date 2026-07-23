import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Integer, Numeric, String, Text, ForeignKey, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


# ── 车辆档案 ──────────────────────────────────────────────────────────────────

class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="车辆编号")
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="车牌号")
    vehicle_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="车辆名称")
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="车辆类型: van/truck/pickup/sedan/electric/tricycle/rented/other")
    brand_model: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="品牌型号")
    color: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="颜色")
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="购买日期")
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False, comment="状态: available/assigned/in_use/maintenance/disabled/scrapped/rented")
    department: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="所属部门")
    default_driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="默认司机")
    load_capacity: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="载重信息")
    seats: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="座位数")
    vehicle_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="车辆照片")
    license_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="行驶证照片")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    default_driver: Mapped["VehicleDriver | None"] = relationship(
        "VehicleDriver", foreign_keys=[default_driver_id], lazy="selectin",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="vehicle", lazy="selectin",
        primaryjoin="and_(Attachment.related_type=='vehicle', foreign(Attachment.related_id)==Vehicle.id)",
        viewonly=True,
    )


# ── 司机档案 ──────────────────────────────────────────────────────────────────

class VehicleDriver(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicle_drivers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="绑定员工")
    driver_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="司机姓名")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号")
    license_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="驾驶证号")
    license_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="驾驶证类型: A1/A2/B1/B2/C1/C2/etc")
    license_expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="驾驶证到期日")
    is_external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否外协司机")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/disabled")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    employee: Mapped["User | None"] = relationship("User", foreign_keys=[employee_id], lazy="selectin")


# ── 用车申请 ──────────────────────────────────────────────────────────────────

class VehicleUseRequest(Base, TimestampMixin):
    __tablename__ = "vehicle_use_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="申请单号")
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="申请人")
    reason: Mapped[str] = mapped_column(String(32), nullable=False, comment="用车原因: installation/delivery/purchase/after_sales/field/customer_measure/other")
    related_customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, comment="关联客户")
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True, comment="关联订单")
    related_install_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("installation_tasks.id"), nullable=True, comment="关联安装任务")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="出发时间")
    expected_return_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预计返回时间")
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="目的地")
    need_driver: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否需要司机")
    need_cargo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要装货")
    cargo_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="货物说明")
    estimated_distance_km: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, comment="预计里程(km)")
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, comment="状态: draft/pending/approved/rejected/dispatched/cancelled/completed")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="审批人")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审批时间")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="驳回原因")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    requester: Mapped["User | None"] = relationship("User", foreign_keys=[requester_id], lazy="selectin")
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approver_id], lazy="selectin")
    customer: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[related_customer_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_use_requests_requester_id", "requester_id"),
        Index("ix_vehicle_use_requests_status", "status"),
    )


# ── 派车单 ──────────────────────────────────────────────────────────────────

class VehicleDispatch(Base, TimestampMixin):
    __tablename__ = "vehicle_dispatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="派车单号")
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_use_requests.id"), nullable=True, comment="用车申请")
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="司机")
    companions: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="随车人员")
    related_customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, comment="关联客户")
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True, comment="关联订单")
    related_install_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("installation_tasks.id"), nullable=True, comment="关联安装任务")
    start_location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="出发地点")
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="目的地")
    planned_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="计划出发时间")
    planned_return_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="计划返回时间")
    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际出发时间")
    actual_return_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际返回时间")
    start_mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="出车里程(km)")
    end_mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="收车里程(km)")
    actual_distance_km: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, comment="实际行驶里程(km)")
    status: Mapped[str] = mapped_column(String(32), default="assigned", nullable=False, comment="状态: assigned/started/arrived/completed/returned/cancelled/abnormal")
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否有异常")
    abnormal_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="创建人")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    driver: Mapped["VehicleDriver | None"] = relationship("VehicleDriver", foreign_keys=[driver_id], lazy="selectin")
    request: Mapped["VehicleUseRequest | None"] = relationship("VehicleUseRequest", foreign_keys=[request_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_dispatches_vehicle_id_planned", "vehicle_id", "planned_start_time", "planned_return_time"),
        Index("ix_vehicle_dispatches_driver_id", "driver_id"),
        Index("ix_vehicle_dispatches_related_order_id", "related_order_id"),
        Index("ix_vehicle_dispatches_status", "status"),
    )


# ── 出车/收车台账 ────────────────────────────────────────────────────────────

class VehicleTripRecord(Base, TimestampMixin):
    __tablename__ = "vehicle_trip_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="台账编号")
    dispatch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_dispatches.id"), nullable=False, comment="派车单")
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="司机")
    trip_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="出车日期")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="出车时间")
    return_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="收车时间")
    start_mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="出车里程")
    end_mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="收车里程")
    distance_km: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, comment="实际公里数")
    start_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="出车照片")
    return_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="收车照片")
    start_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="出车备注")
    return_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="收车备注")
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否有异常")
    abnormal_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常说明")

    # relationships
    dispatch: Mapped["VehicleDispatch | None"] = relationship("VehicleDispatch", foreign_keys=[dispatch_id], lazy="selectin")
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    driver: Mapped["VehicleDriver | None"] = relationship("VehicleDriver", foreign_keys=[driver_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_trip_records_vehicle_id_trip_date", "vehicle_id", "trip_date"),
        Index("ix_vehicle_trip_records_dispatch_id", "dispatch_id"),
    )


# ── 油费记录 ──────────────────────────────────────────────────────────────────

class VehicleFuelRecord(Base, TimestampMixin):
    __tablename__ = "vehicle_fuel_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="司机")
    dispatch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_dispatches.id"), nullable=True, comment="派车单")
    fuel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="加油时间")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="金额")
    liters: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, comment="升数")
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, comment="单价")
    gas_station: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="加油站")
    mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="当前里程")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="支付方式: cash/wechat/alipay/card/company")
    payer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="付款人")
    is_driver_advance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否司机垫付")
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="票据照片")
    status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False, comment="审核状态: pending_review/approved/rejected/reimbursed/paid")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    driver: Mapped["VehicleDriver | None"] = relationship("VehicleDriver", foreign_keys=[driver_id], lazy="selectin")
    dispatch: Mapped["VehicleDispatch | None"] = relationship("VehicleDispatch", foreign_keys=[dispatch_id], lazy="selectin")
    payer: Mapped["User | None"] = relationship("User", foreign_keys=[payer_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_fuel_records_vehicle_id_fuel_time", "vehicle_id", "fuel_time"),
        Index("ix_vehicle_fuel_records_status", "status"),
    )


# ── 维修保养记录 ──────────────────────────────────────────────────────────────

class VehicleMaintenanceRecord(Base, TimestampMixin):
    __tablename__ = "vehicle_maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    maintenance_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="类型: repair/maintenance/tire/battery/other")
    maintenance_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="维修日期")
    maintenance_item: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="维修项目")
    repair_shop: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="维修厂")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="金额")
    mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="当前里程")
    next_maintenance_mileage: Mapped[float | None] = mapped_column(Numeric(12, 1), nullable=True, comment="下次保养里程")
    next_maintenance_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="下次保养日期")
    handler_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="经办人")
    invoice_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="发票照片")
    before_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="维修前照片")
    after_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="维修后照片")
    status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False, comment="审核状态: pending_review/approved/rejected/paid")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    handler: Mapped["User | None"] = relationship("User", foreign_keys=[handler_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_maintenance_records_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_maintenance_records_status", "status"),
    )


# ── 保险/年检/证件 ────────────────────────────────────────────────────────────

class VehicleCertificate(Base, TimestampMixin):
    __tablename__ = "vehicle_certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="司机(驾驶证用)")
    certificate_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="证件类型: compulsory_insurance/commercial_insurance/annual_inspection/driving_license/transport_license/driver_license/maintenance/other")
    certificate_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证件编号")
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始日期")
    expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="到期日期")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="金额")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="附件")
    reminder_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False, comment="提前提醒天数")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/expired/renewed/cancelled")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    driver: Mapped["VehicleDriver | None"] = relationship("VehicleDriver", foreign_keys=[driver_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_certificates_vehicle_id_expire_date", "vehicle_id", "expire_date"),
        Index("ix_vehicle_certificates_certificate_type", "certificate_type"),
    )


# ── 违章/事故/异常 ────────────────────────────────────────────────────────────

class VehicleIncident(Base, TimestampMixin):
    __tablename__ = "vehicle_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_drivers.id"), nullable=True, comment="司机")
    dispatch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_dispatches.id"), nullable=True, comment="派车单")
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True, comment="关联订单")
    related_install_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("installation_tasks.id"), nullable=True, comment="关联安装任务")
    incident_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="事件类型: traffic_violation/accident/scratch/vehicle_damage/customer_complaint/traffic_penalty/site_issue/other")
    incident_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发生时间")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="发生地点")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="事件描述")
    fine_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="罚款金额")
    points_deducted: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="扣分")
    repair_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="维修金额")
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="责任人")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="处理状态: pending/processing/resolved/closed/disputed")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理结果")
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="证据照片")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    driver: Mapped["VehicleDriver | None"] = relationship("VehicleDriver", foreign_keys=[driver_id], lazy="selectin")
    dispatch: Mapped["VehicleDispatch | None"] = relationship("VehicleDispatch", foreign_keys=[dispatch_id], lazy="selectin")
    responsible_user: Mapped["User | None"] = relationship("User", foreign_keys=[responsible_user_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_incidents_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_incidents_status", "status"),
        Index("ix_vehicle_incidents_incident_type", "incident_type"),
    )


# ── 费用分摊 ──────────────────────────────────────────────────────────────────

class VehicleCostAllocation(Base, TimestampMixin):
    __tablename__ = "vehicle_cost_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="来源类型: fuel/maintenance/insurance/inspection/violation/other")
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="来源记录ID")
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, comment="车辆")
    dispatch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicle_dispatches.id"), nullable=True, comment="派车单")
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=True, comment="关联订单")
    related_install_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("installation_tasks.id"), nullable=True, comment="关联安装任务")
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="费用类型: fuel/toll/parking/repair/maintenance/insurance/inspection/violation/accident/tire/battery/wash/rent/driver_subsidy/other")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False, comment="金额")
    allocation_method: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="分摊方式: manual/auto_dispatch/auto_order")
    allocation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="分摊日期")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # relationships
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", foreign_keys=[vehicle_id], lazy="selectin")
    dispatch: Mapped["VehicleDispatch | None"] = relationship("VehicleDispatch", foreign_keys=[dispatch_id], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_cost_allocations_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_cost_allocations_related_order_id", "related_order_id"),
        Index("ix_vehicle_cost_allocations_source_type_id", "source_type", "source_id"),
    )


# ── Agent 消息识别草稿 ─────────────────────────────────────────────────────────

class VehicleAgentDraft(Base, TimestampMixin):
    __tablename__ = "vehicle_agent_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, comment="识别意图: vehicle_use_request/vehicle_dispatch/vehicle_start/vehicle_arrival/vehicle_return/fuel_expense/vehicle_issue/maintenance_request/vehicle_query")
    confidence: Mapped[float] = mapped_column(Numeric(4, 2), default=0, nullable=False, comment="置信度 0.00-1.00")
    risk_level: Mapped[str] = mapped_column(String(16), default="medium", nullable=False, comment="风险等级: low/medium/high")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="状态: pending/confirmed/rejected/expired")
    platform: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="消息来源: workbuddy_wechat/feishu/wechat/manual/other")
    conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="会话ID")
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="消息ID")
    sender_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="发送者姓名")
    sender_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="发送者ID")
    original_content: Mapped[str] = mapped_column(Text, nullable=False, comment="原始消息文本")
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="提取的结构化数据")
    suggested_action: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="建议操作")
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否需要人工确认")
    requires_finance_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要财务审核")
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="确认人")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="确认时间")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="驳回原因")
    created_draft_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="确认后创建的正式记录ID")
    created_draft_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="确认后创建的记录类型: fuel/maintenance/dispatch/request/incident")

    # relationships
    confirmed_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[confirmed_by], lazy="selectin")

    __table_args__ = (
        Index("ix_vehicle_agent_drafts_status", "status"),
        Index("ix_vehicle_agent_drafts_intent", "intent"),
        Index("ix_vehicle_agent_drafts_platform", "platform"),
    )
