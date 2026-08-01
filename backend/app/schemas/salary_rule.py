from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class SalaryRuleCreate(BaseModel):
    employee_id: str
    effective_date: date
    base_salary: float = 0
    social_insurance: Optional[float] = None
    remark: Optional[str] = None


class SalaryRuleUpdate(BaseModel):
    effective_date: Optional[date] = None
    base_salary: Optional[float] = None
    social_insurance: Optional[float] = None
    remark: Optional[str] = None


class SalaryRuleResponse(BaseModel):
    id: str
    employee_id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    effective_date: date
    base_salary: float
    social_insurance: Optional[float] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
