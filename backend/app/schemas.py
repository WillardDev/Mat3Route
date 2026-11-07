from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AccidentSeverity = Literal["low", "medium", "high"]
AccidentStatus = Literal["reported", "verified", "resolved", "rejected"]
NotificationType = Literal["weather", "surge", "accident", "system"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Users and devices
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    phone: str = Field(min_length=7, max_length=24)
    name: str | None = None
    email: str | None = None
    city: str = "Nairobi"
    route_id: int | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    city: str | None = None
    route_id: int | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None


class UserOut(ORMModel):
    id: int
    phone: str
    name: str | None
    email: str | None
    city: str
    route_id: int | None
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime


class DeviceCreate(BaseModel):
    provider: str = Field(default="thrivewave", min_length=2, max_length=32)
    token: str = Field(min_length=1, max_length=512)
    platform: str | None = Field(default=None, max_length=32)


class DeviceOut(ORMModel):
    id: int
    user_id: int
    provider: str
    token: str
    platform: str | None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Routes and fares
# ---------------------------------------------------------------------------
class RouteOut(BaseModel):
    id: int
    line: str
    route_number: str
    start: str
    end: str
    sacco: str
    sacco_code: str
    base_fare_min: int
    base_fare_max: int
    start_lat: float | None = None
    start_lon: float | None = None
    end_lat: float | None = None
    end_lon: float | None = None
    path: list[list[float]] | None = None


class FarePreviewOut(BaseModel):
    route_id: int
    line: str
    route_number: str
    start: str
    end: str
    base_fare_min: int
    base_fare_max: int
    fare_min: int
    fare_max: int
    multiplier: float
    components: dict[str, float]
    reasons: list[str]
    surge_event_id: int | None
    surge_ends_at: datetime | None
    active: bool


class FareQuoteCreate(BaseModel):
    route_id: int
    user_id: int | None = None


class FareQuoteOut(BaseModel):
    id: int
    user_id: int | None
    route_id: int
    surge_event_id: int | None
    multiplier: float
    base_fare_min: int
    base_fare_max: int
    fare_min: int
    fare_max: int
    quoted_at: datetime
    expires_at: datetime


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
class WeatherOut(ORMModel):
    id: int
    city: str
    latitude: float
    longitude: float
    condition_code: int | None
    condition_main: str
    description: str
    temperature_c: float
    feels_like_c: float
    humidity: int | None
    wind_speed_mps: float | None
    observed_at: datetime
    fetched_at: datetime


class WeatherRefreshOut(BaseModel):
    snapshot: WeatherOut
    significant_change: bool
    direction: str
    reason: str | None
    surge_events_updated: int


# ---------------------------------------------------------------------------
# Accidents
# ---------------------------------------------------------------------------
class AccidentCreate(BaseModel):
    route_id: int
    reported_by_user_id: int | None = None
    description: str = Field(min_length=3, max_length=1000)
    severity: AccidentSeverity = "medium"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class AccidentStatusUpdate(BaseModel):
    status: AccidentStatus


class AccidentOut(ORMModel):
    id: int
    route_id: int
    reported_by_user_id: int | None
    description: str
    severity: str
    status: str
    latitude: float | None
    longitude: float | None
    reported_at: datetime
    resolved_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Surges
# ---------------------------------------------------------------------------
class SurgeOut(ORMModel):
    id: int
    route_id: int | None
    trigger_type: str
    multiplier: float
    weather_component: float
    accident_component: float
    peak_component: float
    base_fare_min: int
    base_fare_max: int
    adjusted_fare_min: int
    adjusted_fare_max: int
    reason: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    weather_snapshot_id: int | None
    accident_report_id: int | None
    created_at: datetime
    updated_at: datetime


class SurgeRecalculateOut(BaseModel):
    routes_evaluated: int
    active_surges: int


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class NotificationOut(ORMModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    body: str
    provider: str
    provider_message_id: str | None
    status: str
    error: str | None
    payload: dict[str, Any] | None
    sent_at: datetime | None
    created_at: datetime


class NotificationTestRequest(BaseModel):
    user_id: int
    title: str = Field(default="Mat3 test notification", min_length=1, max_length=120)
    body: str = Field(
        default="Push notifications are working. Safe travels!",
        min_length=1,
        max_length=500,
    )
