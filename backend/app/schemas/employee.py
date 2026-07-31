from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class EmployeeCreate(BaseModel):
    employee_no: Optional[str] = None
    name: str; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str = "active"; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool = True

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: Optional[str] = None; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: Optional[bool] = None

class EmployeeResponse(BaseModel):
    id: str; employee_no: str; name: str; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}