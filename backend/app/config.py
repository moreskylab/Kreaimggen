from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "KreaImgGen"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-strong-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 20

    # Celery / Broker
    CELERY_BROKER_URL: str = "amqp://guest:guest@rabbitmq:5672//"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Krea AI
    KREA_API_KEY: str = ""
    KREA_API_BASE_URL: str = "https://api.krea.ai/v1"

    # Redis (for rate limiting state)
    REDIS_URL: str = "redis://redis:6379/1"

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://kreaimggen:kreaimggen@postgres:5432/kreaimggen"
    # Sync URL for Alembic (uses psycopg2)
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://kreaimggen:kreaimggen@postgres:5432/kreaimggen"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
