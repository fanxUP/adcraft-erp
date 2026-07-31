from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SalaryRecordCreate(BaseModel):
    employee_id: str
    month: str
    base_salary: float
    overtime_pay: Optional[float] = None
    bonus: Optional[float] = None
    commission: Optional[float] = None
    subsidy: Optional[float] = None
    deduction: Optional[float] = None
    net_salary: float
    payment_status: str = "pending"
    remark: Optional[str] = None


class SalaryRecordUpdate(BaseModel):
    base_salary: Optional[float] = None
    overtime_pay: Optional[float] = None
    bonus: Optional[float] = None
    commission: Optional[float] = None
    subsidy: Optional[float] = None
    deduction: Optional[float] = None
    net_salary: Optional[float] = None
    payment_status: Optional[str] = None
    paid_at: Optional[datetime] = None
    remark: Optional[str] = None


class SalaryRecordResponse(BaseModel):
    id: str
    employee_id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    month: str
    base_salary: float
    overtime_pay: Optional[float] = None
    bonus: Optional[float] = None
    commission: Optional[float] = None
    subsidy: Optional[float] = None
    deduction: Optional[float] = None
    net_salary: float
    payment_status: str
    paid_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SalaryGenerateRequest(BaseModel):
    """按工资规则自动生成工资表的请求。employee_ids 为空时生成全部在职员工。"""
    month: str
    employee_ids: Optional[list[str]] = None
