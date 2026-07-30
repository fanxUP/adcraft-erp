from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    duration_days: float
    reason: str
    remark: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    leave_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[float] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class LeaveRequestApprove(BaseModel):
    status: str  # approved/rejected
    remark: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    id: str
    employee_id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    duration_days: float
    reason: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
