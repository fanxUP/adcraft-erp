from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    real_name: str | None = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserProfile(BaseModel):
    id: str
    username: str
    real_name: str | None
    phone: str | None
    email: str | None
    is_active: bool
    must_change_password: bool = False
    roles: list[str] = []

    model_config = {"from_attributes": True}
