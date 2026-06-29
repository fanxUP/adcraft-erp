from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AdCraft ERP"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change_me"

    DATABASE_URL: str = "postgresql+asyncpg://adcraft:adcraft_dev_password@postgres:5432/adcraft_erp"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://adcraft:adcraft_dev_password@postgres:5432/adcraft_erp"

    REDIS_URL: str = "redis://redis:6379/0"

    UPLOAD_STORAGE: str = "local"
    LOCAL_UPLOAD_DIR: str = "/app/uploads"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "minio_dev_password"
    MINIO_BUCKET: str = "adcraft-files"

    JWT_EXPIRE_MINUTES: int = 1440

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
