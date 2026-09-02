from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AdCraft ERP"
    COMPANY_NAME: str = ""
    COMPANY_PHONE: str = ""
    APP_ENV: str = "development"
    SECRET_KEY: str = ""  # MUST be set via .env for production — generate with: openssl rand -hex 32
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Credentials belong in .env; keep source fallbacks password-free so a
    # development default cannot accidentally become a deployed credential.
    DATABASE_URL: str = "postgresql+asyncpg://adcraft@127.0.0.1:5432/adcraft_erp"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://adcraft@127.0.0.1:5432/adcraft_erp"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    UPLOAD_STORAGE: str = "local"
    LOCAL_UPLOAD_DIR: str = "./uploads"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = ""
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
    AI_BUSINESS_RULE_SYNC_ON_STARTUP: bool = True

    # Rate limiting (API throttling via Redis)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 120        # default requests per window
    RATE_LIMIT_WINDOW: int = 60          # window in seconds

    # 执行中订单明细变更灰度开关：可通过环境变量关闭入口，不改业务数据。
    ORDER_ITEM_ASSOCIATED_EDIT_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
