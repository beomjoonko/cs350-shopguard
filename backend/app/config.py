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

    # ─── Database ───────────────────────────────────────────
    DATABASE_URL: str = "mysql+pymysql://shopguard:changeme@mysql:3306/shopguard"

    # ─── Redis ──────────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # ─── JWT (SRS §5.3) ─────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Argon2 (SRS §5.3, RFC 9106) ────────────────────────
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    # ─── Rate limiting (SRS §4.8 REQ-1) ─────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ─── Account lockout (SRS §4.1 REQ-3) ───────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30

    # ─── Password policy (SRS §4.3 REQ-6) ───────────────────
    PASSWORD_MIN_LENGTH: int = 8

    # ─── CORS ───────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ─── Object storage ─────────────────────────────────────
    S3_ENDPOINT: str | None = None
    S3_BUCKET: str = "shopguard-evidence"
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
