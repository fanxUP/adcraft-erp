"""AI Assistant configuration (env vars)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AiAssistantSettings(BaseSettings):
    AI_ASSISTANT_ENABLED: bool = True
    AI_MAX_HISTORY_MESSAGES: int = 20
    AI_STREAM_ENABLED: bool = True
    AI_TOOL_CALL_TIMEOUT_SECONDS: int = 20
    AI_PENDING_ACTION_EXPIRE_MINUTES: int = 30
    AI_DEFAULT_TEMPERATURE: float = 0.2

    AI_ALLOW_WRITE_ACTIONS: bool = True
    AI_ALLOW_FINANCE_WRITE_ACTIONS: bool = False
    AI_ALLOW_DELETE_ACTIONS: bool = False
    AI_REQUIRE_CONFIRMATION: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = AiAssistantSettings()
