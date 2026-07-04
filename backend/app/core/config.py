# Tech Nebula - Core Configuration
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Tech Nebula"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

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

    # Crawl cache TTL (seconds)
    CRAWL_CACHE_TTL: int = 3600  # 1 hour default

    # AI interpretation cache TTL (seconds)
    AI_CACHE_TTL: int = 86400  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
