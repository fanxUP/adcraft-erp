from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.core.password_policy import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, validate_new_password


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    role_ids: list[str] = []

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        validate_new_password(value)
        return value


class UserUpdate(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None
    role_ids: list[str] | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    created_at: datetime | None = None
    roles: list[str] = []

    model_config = {"from_attributes": True}
