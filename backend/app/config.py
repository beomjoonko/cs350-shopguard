"""
Application settings.

Loaded from environment variables (or .env file in dev).
See SRS §5.3 (Security) and §4.8 (System Guardrails) for the source-of-truth
values that these settings must enforce.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── App ────────────────────────────────────────────────
    APP_NAME: str = "ShopGuard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ─── Database (Supabase PostgreSQL) ─────────────────────
    DATABASE_URL: str = "postgresql+psycopg2://postgres:changeme@db.xxx.supabase.co:5432/postgres"

    # ─── Redis ──────────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # ─── Supabase ───────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = "change-me-in-production"  # Settings → API → JWT Settings
    SUPABASE_STORAGE_BUCKET: str = "shopguard-evidence"

    # ─── Rate limiting (SRS §4.8 REQ-1) ─────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ─── Password policy (SRS §4.3 REQ-6) ───────────────────
    PASSWORD_MIN_LENGTH: int = 8

    # ─── CORS ───────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
