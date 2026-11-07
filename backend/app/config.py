"""Application configuration via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — Fly.io sets DATABASE_URL as postgres://…; we normalise to asyncpg driver.
    database_url: str = "postgresql+asyncpg://mat3route:ae0047f332102cc2b8b11f11da3e2a63@localhost:5432/mat3route_dev"

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL regardless of how DATABASE_URL is set."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # In Fly.io, mat3route-db.internal provides direct internal DNS to Postgres
        if "mat3route-db.flycast" in url:
            url = url.replace("mat3route-db.flycast", "mat3route-db.internal")

        # Strip sslmode parameters that asyncpg doesn't accept as URL query params
        if "?sslmode=" in url:
            url = url.split("?sslmode=")[0]
        elif "&sslmode=" in url:
            url = url.split("&sslmode=")[0]
        return url

    # ThriveWave / ThriveVas SMS API
    thrivewave_api_key: str = ""
    thrivewave_api_url: str = "https://api.thrivevas.com/v1"
    thrivewave_sender_id: str = "Mat3Route"

    # App
    app_name: str = "Mat3Route API"
    app_version: str = "1.0.0"
    debug: bool = False

    # CORS origins - comma-separated list or *
    allowed_origins: str = "*"

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
