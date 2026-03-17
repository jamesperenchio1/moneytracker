from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Database — local defaults                                           #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # ------------------------------------------------------------------ #
    # Supabase / Vercel native integration                                #
    # Vercel injects these automatically when the Supabase integration is  #
    # connected via the Vercel marketplace.                               #
    # ------------------------------------------------------------------ #
    # Direct (non-pooled) connection — used by asyncpg and Alembic.
    POSTGRES_URL_NON_POOLING: str = ""
    # Pooled connection — used by Celery workers (psycopg2).
    POSTGRES_URL: str = ""

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # ------------------------------------------------------------------ #
    # Redis                                                               #
    # ------------------------------------------------------------------ #
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------ #
    # Security                                                            #
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ------------------------------------------------------------------ #
    # Market Data                                                         #
    # ------------------------------------------------------------------ #
    YAHOO_FINANCE_ENABLED: bool = True
    ALPHA_VANTAGE_API_KEY: str = ""
    POLYGON_API_KEY: str = ""

    # ------------------------------------------------------------------ #
    # File Upload                                                         #
    # ------------------------------------------------------------------ #
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"

    # ------------------------------------------------------------------ #
    # Scraping                                                            #
    # ------------------------------------------------------------------ #
    PLAYWRIGHT_HEADLESS: bool = True

    # ------------------------------------------------------------------ #
    # App                                                                 #
    # ------------------------------------------------------------------ #
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    # ------------------------------------------------------------------ #
    # Resolved URLs (Supabase vars take priority over explicit DATABASE_URL)
    # ------------------------------------------------------------------ #

    @property
    def database_url_async(self) -> str:
        """asyncpg URL for SQLAlchemy async engine."""
        raw = (
            self.DATABASE_URL
            or self.POSTGRES_URL_NON_POOLING
            or self.POSTGRES_URL
            or "postgresql+asyncpg://moneytracker:moneytracker@localhost:5432/moneytracker"
        )
        # Normalise scheme for asyncpg
        return (
            raw
            .replace("postgres://", "postgresql+asyncpg://", 1)
            .replace("postgresql://", "postgresql+asyncpg://", 1)
        )

    @property
    def database_url_sync(self) -> str:
        """psycopg2 URL for Alembic / Celery workers."""
        raw = (
            self.DATABASE_URL_SYNC
            or self.POSTGRES_URL_NON_POOLING
            or self.POSTGRES_URL
            or "postgresql://moneytracker:moneytracker@localhost:5432/moneytracker"
        )
        # Normalise scheme for psycopg2
        return (
            raw
            .replace("postgresql+asyncpg://", "postgresql://", 1)
            .replace("postgres://", "postgresql://", 1)
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
