from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.models import AccidentReport, WeatherSnapshot
from app.providers.mock import MockNotificationProvider
from app.services.notifications import NotificationService
from app.services.surge import SurgeService


def make_service(db, settings):
    provider = MockNotificationProvider()
    notifications = NotificationService(db, settings, provider)
    return SurgeService(db, settings, notifications), provider


def test_combined_triggers_and_cap(db, route):
    settings = Settings(
        database_url="sqlite://",
        notification_provider="mock",
        max_surge_multiplier=1.5,
        timezone="Africa/Nairobi",
    )
    now = datetime(2026, 11, 2, 18, 0, tzinfo=ZoneInfo("Africa/Nairobi"))
    db.add(
        WeatherSnapshot(
            city="Nairobi",
            latitude=-1.2921,
            longitude=36.8219,
            condition_main="Thunderstorm",
            description="thunderstorm with heavy rain",
            temperature_c=19.0,
            feels_like_c=19.0,
            observed_at=now,
        )
    )
    db.add(
        AccidentReport(
            route_id=route.id,
            description="Collision",
            severity="high",
            status="reported",
            reported_at=now,
        )
    )
    db.commit()

    service, _ = make_service(db, settings)
    result = service.compute(route, now=now)

    assert result.weather_component == 0.35
    assert result.accident_component == 0.35
    assert result.peak_component == 0.25
    assert result.multiplier == 1.5
    assert result.fare_min >= route.fare_min
    assert "maximum surge cap applied" in result.reasons


def test_surge_event_is_reused_between_refreshes(db, route):
    settings = Settings(database_url="sqlite://", notification_provider="mock")
    now = datetime(2026, 11, 2, 12, 0, tzinfo=ZoneInfo("Africa/Nairobi"))
    db.add(
        WeatherSnapshot(
            city="Nairobi",
            latitude=-1.2921,
            longitude=36.8219,
            condition_main="Rain",
            description="light rain",
            temperature_c=20.0,
            feels_like_c=20.0,
            observed_at=now,
        )
    )
    db.commit()

    service, _ = make_service(db, settings)
    first = service.refresh_route(route, notify=True, now=now)
    assert first is not None
    second = service.refresh_route(
        route, notify=True, now=now + timedelta(minutes=1)
    )

    assert second is not None
    assert second.id == first.id
    assert second.multiplier == first.multiplier
