# Tech Nebula - Core Configuration
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    # Application
    APP_NAME: str = "Tech Nebula"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOCAL_MODE: bool = True
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/technebula"
    DATABASE_SYNC_URL: str = "postgresql://user:pass@localhost:5432/technebula"

    # Redis / Upstash
    REDIS_URL: str = "redis://localhost:6379"
    UPSTASH_REST_URL: str = ""
    UPSTASH_REST_TOKEN: str = ""

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI API (Platform unified)
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Crawl cache TTL (seconds)
    CRAWL_CACHE_TTL: int = 3600  # 1 hour default

    # AI interpretation cache TTL (seconds)
    AI_CACHE_TTL: int = 86400  # 24 hours

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
