from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


class OperationLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    action: str
    before_data: dict | None = None
    after_data: dict | None = None
    ip_address: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class OperationLogQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    user_id: str | None = None
    object_type: str | None = None
    action: str | None = None
    date_from: date | None = None
    date_to: date | None = None
