"""Application settings, loaded from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS = {
    "insecure-dev-secret-change-me",
    "change-this-to-a-long-random-string-in-production",
}


class Settings(BaseSettings):
    """All configuration for the API, with safe defaults for local development."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://taskuser:taskpass@localhost:5432/taskdb"
    TEST_DATABASE_URL: str = "postgresql+psycopg2://taskuser:taskpass@localhost:5432/taskdb_test"

    SECRET_KEY: str = "insecure-dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Task Management API"
    API_V1_PREFIX: str = "/api/v1"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    SENTRY_RELEASE: str | None = None

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_REFRESH: str = "30/minute"
    TRUST_PROXY_HEADERS: bool | None = None

    MAX_REQUEST_BODY_BYTES: int = 1_000_000
    ENABLE_DEBUG_ROUTES: bool = False

    @field_validator("SENTRY_DSN", "SENTRY_RELEASE", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        """Treat an empty environment variable the same as an unset one."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def refuse_weak_secret_in_production(self):
        """Fail fast at startup if production is configured with a weak JWT secret."""
        if self.is_production and (
            self.SECRET_KEY in INSECURE_SECRET_KEYS or len(self.SECRET_KEY) < 32
        ):
            raise ValueError(
                "SECRET_KEY must be a random string of at least 32 characters "
                "when ENVIRONMENT=production"
            )
        return self

    @property
    def is_production(self) -> bool:
        """True when running with ENVIRONMENT=production."""
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def trust_proxy_headers(self) -> bool:
        """Whether to read the client IP from X-Forwarded-For (on by default in production)."""
        if self.TRUST_PROXY_HEADERS is None:
            return self.is_production
        return self.TRUST_PROXY_HEADERS

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS split into a clean list of origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()


settings = get_settings()
