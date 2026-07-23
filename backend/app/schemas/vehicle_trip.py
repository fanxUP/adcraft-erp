from pydantic import BaseModel


class DispatchStart(BaseModel):
    start_time: str | None = None
    start_mileage: float | None = None
    start_photo_url: str | None = None
    start_remark: str | None = None


class DispatchArrive(BaseModel):
    arrive_remark: str | None = None


class DispatchReturn(BaseModel):
    return_time: str | None = None
    end_mileage: float | None = None
    return_photo_url: str | None = None
    return_remark: str | None = None
    abnormal_flag: bool = False
    abnormal_description: str | None = None
