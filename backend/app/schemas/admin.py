from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePermissionUpdate(BaseModel):
    permission_ids: list[str] = []


class SettingsUpdate(BaseModel):
    APP_NAME: str | None = None
    JWT_EXPIRE_MINUTES: int | None = None
    AI_ENABLED: bool | None = None
    AI_PROVIDER: str | None = None
    AI_MODEL: str | None = None
    AI_API_KEY: str | None = None
    AI_API_BASE_URL: str | None = None
