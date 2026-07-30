from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Optional

class AttendanceRuleCreate(BaseModel):
    name: str; department: Optional[str] = None; check_in_time: time; check_out_time: time
    work_days: Optional[list[str]] = None; late_threshold: int = 0; early_leave_threshold: int = 0
    overtime_rate: float = 1.5; is_active: bool = True

class AttendanceRuleUpdate(BaseModel):
    name: Optional[str] = None; department: Optional[str] = None; check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None; work_days: Optional[list[str]] = None
    late_threshold: Optional[int] = None; early_leave_threshold: Optional[int] = None
    overtime_rate: Optional[float] = None; is_active: Optional[bool] = None

class AttendanceRuleResponse(BaseModel):
    id: str; name: str; department: Optional[str] = None; check_in_time: str; check_out_time: str
    work_days: Optional[list] = None; late_threshold: int = 0; early_leave_threshold: int = 0
    overtime_rate: Optional[float] = None; is_active: bool; created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None; model_config = {"from_attributes": True}

class AttendanceRecordCreate(BaseModel):
    employee_id: str; date: date; check_in_time: Optional[datetime] = None; check_out_time: Optional[datetime] = None
    check_in_status: str = "normal"; check_out_status: str = "normal"; source: str = "manual_input"
    remark: Optional[str] = None; overtime_hours: Optional[float] = 0

class AttendanceRecordUpdate(BaseModel):
    check_in_time: Optional[datetime] = None; check_out_time: Optional[datetime] = None
    check_in_status: Optional[str] = None; check_out_status: Optional[str] = None
    remark: Optional[str] = None; overtime_hours: Optional[float] = None

class AttendanceRecordResponse(BaseModel):
    id: str; employee_id: str; date: date; check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None; check_in_status: str; check_out_status: str
    source: str; remark: Optional[str] = None; overtime_hours: Optional[float] = None; created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None; model_config = {"from_attributes": True}