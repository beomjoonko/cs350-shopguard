"""Worker settings — mirrors backend/app/config.py for shared env."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg2://postgres:changeme@db.xxx.supabase.co:5432/postgres"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Crawling (SRS §2.5 — must not overload external platforms)
    CRAWLER_REQUEST_DELAY_MS: int = 1000
    CRAWLER_USER_AGENT: str = "ShopGuardBot/1.0"

    WORKER_CONCURRENCY: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
