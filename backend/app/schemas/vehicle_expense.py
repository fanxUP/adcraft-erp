from pydantic import BaseModel


# ── 油费记录 ──────────────────────────────────────────────────────────────────

class FuelRecordCreate(BaseModel):
    vehicle_id: str
    driver_id: str | None = None
    dispatch_id: str | None = None
    fuel_time: str | None = None
    amount: float = 0
    liters: float | None = None
    unit_price: float | None = None
    gas_station: str | None = None
    mileage: float | None = None
    payment_method: str | None = None
    payer_id: str | None = None
    is_driver_advance: bool = False
    receipt_url: str | None = None
    remark: str | None = None


class FuelRecordUpdate(BaseModel):
    vehicle_id: str | None = None
    driver_id: str | None = None
    dispatch_id: str | None = None
    fuel_time: str | None = None
    amount: float | None = None
    liters: float | None = None
    unit_price: float | None = None
    gas_station: str | None = None
    mileage: float | None = None
    payment_method: str | None = None
    payer_id: str | None = None
    is_driver_advance: bool | None = None
    receipt_url: str | None = None
    remark: str | None = None


class FuelRecordReview(BaseModel):
    status: str  # approved / rejected
    remark: str | None = None


# ── 维修保养记录 ──────────────────────────────────────────────────────────────

class MaintenanceRecordCreate(BaseModel):
    vehicle_id: str
    maintenance_type: str = "maintenance"  # repair/maintenance/tire/battery/other
    maintenance_date: str | None = None
    maintenance_item: str | None = None
    repair_shop: str | None = None
    amount: float = 0
    mileage: float | None = None
    next_maintenance_mileage: float | None = None
    next_maintenance_date: str | None = None
    handler_id: str | None = None
    invoice_url: str | None = None
    before_photo_url: str | None = None
    after_photo_url: str | None = None
    remark: str | None = None


class MaintenanceRecordUpdate(BaseModel):
    vehicle_id: str | None = None
    maintenance_type: str | None = None
    maintenance_date: str | None = None
    maintenance_item: str | None = None
    repair_shop: str | None = None
    amount: float | None = None
    mileage: float | None = None
    next_maintenance_mileage: float | None = None
    next_maintenance_date: str | None = None
    handler_id: str | None = None
    invoice_url: str | None = None
    before_photo_url: str | None = None
    after_photo_url: str | None = None
    remark: str | None = None


class MaintenanceRecordReview(BaseModel):
    status: str  # approved / rejected
    remark: str | None = None


# ── 通用费用 ──────────────────────────────────────────────────────────────────

class CostAllocationCreate(BaseModel):
    source_type: str = "manual"  # fuel/maintenance/insurance/inspection/violation/other/manual
    source_id: str | None = None
    vehicle_id: str
    dispatch_id: str | None = None
    related_order_id: str | None = None
    related_install_task_id: str | None = None
    cost_type: str  # fuel/toll/parking/repair/maintenance/insurance/inspection/violation/accident/tire/battery/wash/rent/driver_subsidy/other
    amount: float = 0
    allocation_method: str = "manual"  # manual/auto_dispatch/auto_order
    allocation_date: str | None = None
    remark: str | None = None


# ── 保险/年检/证件 ──────────────────────────────────────────────────────────

class CertificateCreate(BaseModel):
    vehicle_id: str
    driver_id: str | None = None
    certificate_type: str  # compulsory_insurance/commercial_insurance/annual_inspection/driving_license/transport_license/driver_license/maintenance/other
    certificate_no: str | None = None
    start_date: str | None = None
    expire_date: str | None = None
    amount: float = 0
    file_url: str | None = None
    reminder_days: int = 30
    remark: str | None = None


class CertificateUpdate(BaseModel):
    vehicle_id: str | None = None
    driver_id: str | None = None
    certificate_type: str | None = None
    certificate_no: str | None = None
    start_date: str | None = None
    expire_date: str | None = None
    amount: float | None = None
    file_url: str | None = None
    reminder_days: int | None = None
    status: str | None = None
    remark: str | None = None