from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from ..config import Settings
from ..models import WeatherSnapshot
from ..utils import utcnow

logger = logging.getLogger(__name__)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WeatherReading:
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
    raw: dict[str, Any]


class OpenWeatherClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch_current(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        city: str | None = None,
    ) -> WeatherReading:
        if not self.settings.openweather_api_key:
            raise WeatherError("OPENWEATHER_API_KEY is not configured")

        lat = latitude if latitude is not None else self.settings.openweather_latitude
        lon = longitude if longitude is not None else self.settings.openweather_longitude
        city_name = city or self.settings.openweather_city

        params: dict[str, object] = {
            "appid": self.settings.openweather_api_key,
            "units": self.settings.openweather_units,
            "lat": lat,
            "lon": lon,
        }
        try:
            response = httpx.get(
                OPENWEATHER_URL,
                params=params,
                timeout=self.settings.openweather_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherError(f"OpenWeatherMap request failed: {exc}") from exc

        data = response.json()
        weather = (data.get("weather") or [{}])[0]
        main = data.get("main") or {}
        wind = data.get("wind") or {}
        observed_at = (
            datetime.fromtimestamp(data["dt"], tz=UTC) if data.get("dt") else utcnow()
        )

        return WeatherReading(
            city=city_name,
            latitude=float(data.get("coord", {}).get("lat", lat)),
            longitude=float(data.get("coord", {}).get("lon", lon)),
            condition_code=weather.get("id"),
            condition_main=weather.get("main") or "Unknown",
            description=weather.get("description") or "unknown",
            temperature_c=float(main.get("temp", 0.0)),
            feels_like_c=float(main.get("feels_like", main.get("temp", 0.0))),
            humidity=main.get("humidity"),
            wind_speed_mps=wind.get("speed"),
            observed_at=observed_at,
            raw=data,
        )


class WeatherService:
    def __init__(self, db, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def save(self, reading: WeatherReading) -> WeatherSnapshot:
        snapshot = WeatherSnapshot(
            city=reading.city,
            latitude=reading.latitude,
            longitude=reading.longitude,
            condition_code=reading.condition_code,
            condition_main=reading.condition_main,
            description=reading.description,
            temperature_c=reading.temperature_c,
            feels_like_c=reading.feels_like_c,
            humidity=reading.humidity,
            wind_speed_mps=reading.wind_speed_mps,
            observed_at=reading.observed_at,
            raw=reading.raw,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def latest(self, city: str | None = None) -> WeatherSnapshot | None:
        from sqlalchemy import func, select

        city_name = city or self.settings.openweather_city
        return self.db.scalar(
            select(WeatherSnapshot)
            .where(func.lower(WeatherSnapshot.city) == city_name.lower())
            .order_by(WeatherSnapshot.observed_at.desc(), WeatherSnapshot.id.desc())
            .limit(1)
        )
