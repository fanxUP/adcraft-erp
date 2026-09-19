from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional
from uuid import UUID


class EmployeeAccountOption(BaseModel):
    id: UUID
    username: str
    real_name: Optional[str] = None


class EmployeeUserBindingRequest(BaseModel):
    # Keep the wire value as text so the service can return the same plain-
    # language message for malformed IDs as it does for other binding errors.
    user_id: Optional[str] = None

class EmployeeCreate(BaseModel):
    employee_no: Optional[str] = None
    name: str; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str = "active"; id_card: Optional[str] = None; education: Optional[str] = None
    license_no: Optional[str] = None; license_type: Optional[str] = None; license_expire_date: Optional[str] = None
    id_card_front_url: Optional[str] = None; id_card_back_url: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    # Accounts are provisioned from the employee record.  These fields are
    # request-only and are never stored on the employee table.
    role_ids: list[str] = []
    initial_password: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool = True

    @field_validator("birth_date", "hire_date", "resignation_date", mode="before")
    @classmethod
    def empty_optional_date_to_none(cls, value):
        return None if value == "" else value

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: Optional[str] = None; id_card: Optional[str] = None; education: Optional[str] = None
    license_no: Optional[str] = None; license_type: Optional[str] = None; license_expire_date: Optional[str] = None
    id_card_front_url: Optional[str] = None; id_card_back_url: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: Optional[bool] = None

    @field_validator("birth_date", "hire_date", "resignation_date", mode="before")
    @classmethod
    def empty_optional_date_to_none(cls, value):
        return None if value == "" else value

class EmployeeResponse(BaseModel):
    id: str; employee_no: str; name: str; phone: Optional[str] = None; gender: Optional[str] = None; ethnicity: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str; id_card: Optional[str] = None; education: Optional[str] = None
    license_no: Optional[str] = None; license_type: Optional[str] = None; license_expire_date: Optional[str] = None
    id_card_front_url: Optional[str] = None; id_card_back_url: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool
    user_username: Optional[str] = None; user_real_name: Optional[str] = None
    user_is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
