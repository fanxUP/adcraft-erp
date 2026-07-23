from pydantic import BaseModel
from datetime import datetime


# ── 车辆档案 ──────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vehicle_code: str
    plate_number: str
    vehicle_name: str
    vehicle_type: str
    brand_model: str | None = None
    color: str | None = None
    purchase_date: datetime | None = None
    department: str | None = None
    default_driver_id: str | None = None
    load_capacity: str | None = None
    seats: int | None = None
    vehicle_photo_url: str | None = None
    license_photo_url: str | None = None
    remark: str | None = None


class VehicleUpdate(BaseModel):
    vehicle_code: str | None = None
    plate_number: str | None = None
    vehicle_name: str | None = None
    vehicle_type: str | None = None
    brand_model: str | None = None
    color: str | None = None
    purchase_date: datetime | None = None
    department: str | None = None
    default_driver_id: str | None = None
    load_capacity: str | None = None
    seats: int | None = None
    vehicle_photo_url: str | None = None
    license_photo_url: str | None = None
    remark: str | None = None
