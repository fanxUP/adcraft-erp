from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class EmploymentHistoryCreate(BaseModel):
    employee_id: str
    change_date: date
    change_type: str
    previous_department: Optional[str] = None
    new_department: Optional[str] = None
    previous_position: Optional[str] = None
    new_position: Optional[str] = None
    reason: Optional[str] = None
    remark: Optional[str] = None


class EmploymentHistoryUpdate(BaseModel):
    change_date: Optional[date] = None
    change_type: Optional[str] = None
    previous_department: Optional[str] = None
    new_department: Optional[str] = None
    previous_position: Optional[str] = None
    new_position: Optional[str] = None
    reason: Optional[str] = None
    remark: Optional[str] = None


class EmploymentHistoryResponse(BaseModel):
    id: str
    employee_id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    change_date: date
    change_type: str
    previous_department: Optional[str] = None
    new_department: Optional[str] = None
    previous_position: Optional[str] = None
    new_position: Optional[str] = None
    reason: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
