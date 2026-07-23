from pydantic import BaseModel
from datetime import datetime


class VehicleDispatchCreate(BaseModel):
    request_id: str | None = None
    vehicle_id: str
    driver_id: str | None = None
    companions: str | None = None
    related_customer_id: str | None = None
    related_order_id: str | None = None
    related_install_task_id: str | None = None
    start_location: str | None = None
    destination: str | None = None
    planned_start_time: datetime | None = None
    planned_return_time: datetime | None = None
    cargo_description: str | None = None
    remark: str | None = None


class VehicleDispatchUpdate(BaseModel):
    vehicle_id: str | None = None
    driver_id: str | None = None
    companions: str | None = None
    related_customer_id: str | None = None
    related_order_id: str | None = None
    related_install_task_id: str | None = None
    start_location: str | None = None
    destination: str | None = None
    planned_start_time: datetime | None = None
    planned_return_time: datetime | None = None
    cargo_description: str | None = None
    remark: str | None = None
