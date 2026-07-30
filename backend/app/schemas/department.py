from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DepartmentCreate(BaseModel):
    name: str
    code: str
    parent_id: Optional[str] = None
    sort_order: int = 0
    description: Optional[str] = None
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    parent_id: Optional[str] = None
    sort_order: int
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
