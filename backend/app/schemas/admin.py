from pydantic import BaseModel, Field, field_validator


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePermissionUpdate(BaseModel):
    permission_ids: list[str] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    APP_NAME: str | None = Field(default=None, max_length=120)
    COMPANY_NAME: str | None = Field(default=None, max_length=200)
    COMPANY_PHONE: str | None = Field(default=None, max_length=64)
    JWT_EXPIRE_MINUTES: int | None = Field(default=None, ge=60, le=10080)
    AI_ENABLED: bool | None = None
    AI_PROVIDER: str | None = Field(default=None, max_length=32)
    AI_MODEL: str | None = Field(default=None, max_length=128)
    AI_API_KEY: str | None = Field(default=None, max_length=512)
    AI_API_BASE_URL: str | None = Field(default=None, max_length=500)

    @field_validator(
        "APP_NAME",
        "COMPANY_NAME",
        "COMPANY_PHONE",
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_API_KEY",
        "AI_API_BASE_URL",
    )
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value is not None and any(ord(char) < 32 for char in value):
            raise ValueError("配置文本不能包含控制字符")
        return value
