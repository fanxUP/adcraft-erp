from datetime import datetime
from pydantic import BaseModel


class VehicleUseRequestCreate(BaseModel):
    reason: str
    related_customer_id: str | None = None
    related_order_id: str | None = None
    related_install_task_id: str | None = None
    start_time: datetime | None = None
    expected_return_time: datetime | None = None
    destination: str | None = None
    need_driver: bool = True
    need_cargo: bool = False
    cargo_description: str | None = None
    estimated_distance_km: float | None = None
    remark: str | None = None


class VehicleUseRequestUpdate(BaseModel):
    reason: str | None = None
    related_customer_id: str | None = None
    related_order_id: str | None = None
    related_install_task_id: str | None = None
    start_time: datetime | None = None
    expected_return_time: datetime | None = None
    destination: str | None = None
    need_driver: bool | None = None
    need_cargo: bool | None = None
    cargo_description: str | None = None
    estimated_distance_km: float | None = None
    remark: str | None = None


class VehicleUseRequestReject(BaseModel):
    reject_reason: str
