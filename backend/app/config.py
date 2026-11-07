"""Application configuration via environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

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
        elif url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

        # In Fly.io, mat3route-db.internal provides direct internal DNS to Postgres
        if "mat3route-db.flycast" in url:
            url = url.replace("mat3route-db.flycast", "mat3route-db.internal")

        # Strip sslmode parameters that asyncpg doesn't accept as URL query params
        if "?sslmode=" in url:
            url = url.split("?sslmode=")[0]
        elif "&sslmode=" in url:
            url = url.split("&sslmode=")[0]
        return url

    @property
    def sync_database_url(self) -> str:
        """Return a psycopg-compatible URL for the synchronous SQLAlchemy stack."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql+asyncpg://"):
            url = "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        if "mat3route-db.flycast" in url:
            url = url.replace("mat3route-db.flycast", "mat3route-db.internal")
        return url

    # Service runtime
    environment: str = "development"
    auto_create_tables: bool = True
    scheduler_enabled: bool = True
    admin_api_token: str = "dev-admin-token"
    timezone: str = "Africa/Nairobi"

    # OpenWeatherMap
    openweather_api_key: str = ""
    openweather_city: str = "Nairobi"
    openweather_latitude: float = -1.2921
    openweather_longitude: float = 36.8219
    openweather_units: str = "metric"
    openweather_timeout_seconds: float = 10.0
    weather_poll_minutes: int = 10

    # ThriveWave / ThriveVas SMS API
    thrivewave_api_key: str = ""
    thrivewave_api_url: str = "https://api.thrivevas.com/v1"
    thrivewave_sender_id: str = "Mat3Route"
    thrivewave_channel: str = "sms"
    thrivewave_base_url: str = "https://sms.thrivevas.com"
    thrivewave_sms_path: str = "/v1/message/send"
    thrivewave_notifications_path: str = "/api/personal-notifications"
    thrivewave_website_id: str = ""
    thrivewave_device_id: str = ""
    thrivewave_sim_subscription_id: str = ""
    thrivewave_callback_url: str = ""
    thrivewave_timeout_seconds: float = 15.0

    # Notifications
    notification_provider: str = "mock"
    notification_batch_size: int = 100

    # Master SMS kill switch. Off by default so no code path can send a real
    # SMS unless it is explicitly enabled. Push notifications are unaffected.
    sms_enabled: bool = False

    # Phone-number login (OTP). While SMS is disabled the demo code is used.
    auth_secret: str = "dev-auth-secret-change-me"
    access_token_ttl_minutes: int = 60
    refresh_token_ttl_days: int = 30
    otp_ttl_minutes: int = 10
    demo_otp_code: str = "4729"

    # Surge engine
    surge_refresh_minutes: int = 5
    surge_ttl_minutes: int = 30
    max_surge_multiplier: float = 2.5
    weather_max_component: float = 0.40
    accident_max_component: float = 0.45
    peak_morning_component: float = 0.20
    peak_evening_component: float = 0.25
    accident_lookback_minutes: int = 120
    quote_ttl_minutes: int = 10

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

    @property
    def cors_origin_list(self) -> list[str]:
        """Alias used by the live-map routers."""
        return self.cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
