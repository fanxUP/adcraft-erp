from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.password_policy import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

THEME_VALUES = frozenset({"light-blue", "light-white", "dark-blue"})
FONT_SIZE_VALUES = frozenset({12, 13, 14, 15, 16, 18, 20})
FONT_WEIGHT_VALUES = frozenset({300, 400, 500, 700})
DEFAULT_USER_PREFERENCES = {
    "theme": "light-blue",
    "font_size": 14,
    "font_weight": 400,
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    real_name: str | None = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @model_validator(mode="after")
    def ensure_new_password_is_different(self):
        if self.old_password == self.new_password:
            raise ValueError("新密码不能与原密码相同")
        return self


ThemeName = Literal["light-blue", "light-white", "dark-blue"]
FontSize = Literal[12, 13, 14, 15, 16, 18, 20]
FontWeight = Literal[300, 400, 500, 700]


class UserPreferencesResponse(BaseModel):
    theme: ThemeName
    font_size: FontSize
    font_weight: FontWeight

    model_config = {"from_attributes": True}


class UserPreferencesUpdate(BaseModel):
    theme: ThemeName | None = None
    font_size: FontSize | None = None
    font_weight: FontWeight | None = None

    @model_validator(mode="after")
    def require_one_preference(self):
        if self.theme is None and self.font_size is None and self.font_weight is None:
            raise ValueError("至少需要设置一项个人偏好")
        return self


class UserProfile(BaseModel):
    id: str
    username: str
    real_name: str | None
    phone: str | None
    email: str | None
    is_active: bool
    must_change_password: bool = False
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    preferences: UserPreferencesResponse

    model_config = {"from_attributes": True}
