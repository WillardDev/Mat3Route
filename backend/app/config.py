from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Mat3 Surge & Alerts"
    environment: str = "development"
    database_url: str = "postgresql+psycopg:///mat3route_dev"
    auto_create_tables: bool = True
    scheduler_enabled: bool = True
    admin_api_token: str = "dev-admin-token"
    timezone: str = "Africa/Nairobi"
    cors_origins: str = "*"

    # OpenWeatherMap
    openweather_api_key: str = ""
    openweather_city: str = "Nairobi"
    openweather_latitude: float = -1.2921
    openweather_longitude: float = 36.8219
    openweather_units: str = "metric"
    openweather_timeout_seconds: float = 10.0
    weather_poll_minutes: int = Field(default=10, ge=1)

    # Notification provider. "mock" works locally without credentials.
    # ThriveVas SMS is the default real channel; set thrivewave_channel="push"
    # to use ThrivePush web push instead.
    notification_provider: str = "mock"
    notification_batch_size: int = Field(default=100, ge=1)
    thrivewave_channel: str = "sms"
    thrivewave_base_url: str = "https://sms.thrivevas.com"
    thrivewave_notifications_path: str = "/api/personal-notifications"
    thrivewave_sms_path: str = "/v1/message/send"
    thrivewave_api_key: str = ""
    thrivewave_sender_id: str = "ThriveVas"
    thrivewave_callback_url: str = ""
    thrivewave_website_id: str = ""
    thrivewave_device_id: str = ""
    thrivewave_sim_subscription_id: str = ""
    thrivewave_timeout_seconds: float = 10.0

    # Surge engine
    surge_refresh_minutes: int = Field(default=5, ge=1)
    surge_ttl_minutes: int = Field(default=30, ge=1)
    max_surge_multiplier: float = Field(default=2.5, ge=1.0)
    weather_max_component: float = Field(default=0.40, ge=0.0)
    accident_max_component: float = Field(default=0.45, ge=0.0)
    peak_morning_component: float = Field(default=0.20, ge=0.0)
    peak_evening_component: float = Field(default=0.25, ge=0.0)
    accident_lookback_minutes: int = Field(default=120, ge=1)
    quote_ttl_minutes: int = Field(default=10, ge=1)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Allow the plain DATABASE_URL from .env while using psycopg 3."""
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
