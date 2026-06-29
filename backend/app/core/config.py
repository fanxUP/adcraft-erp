from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AdCraft ERP"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change_me"

    DATABASE_URL: str = "postgresql+asyncpg://adcraft:adcraft_dev_password@127.0.0.1:5432/adcraft_erp"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://adcraft:adcraft_dev_password@127.0.0.1:5432/adcraft_erp"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    UPLOAD_STORAGE: str = "local"
    LOCAL_UPLOAD_DIR: str = "/app/uploads"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "minio_dev_password"
    MINIO_BUCKET: str = "adcraft-files"

    JWT_EXPIRE_MINUTES: int = 1440

    # AI Feature Configuration (all optional, AI disabled by default)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "anthropic"  # "anthropic" | "openai"
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = ""
    AI_MODEL: str = "claude-sonnet-4-20250514"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
