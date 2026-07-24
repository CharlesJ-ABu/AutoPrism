from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AutoPrism V2"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/autoprism"
    )
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/autoprism"
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_QUEUE_NAME: str = "autoprism:v2:collection"

    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o"
    AI_PROVIDER: str = "openai-compatible"

    ARTIFACT_STORAGE_PATH: str = "./data/artifacts"
    V2_AUTO_CREATE_SCHEMA: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # V1 .env files may contain retired keys; V2 deliberately ignores them.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
