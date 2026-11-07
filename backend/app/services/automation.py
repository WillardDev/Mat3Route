from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AccidentReport, Route, SurgeEvent, WeatherSnapshot
from ..providers import build_provider
from ..providers.base import NotificationProvider
from ..utils import utcnow
from .notifications import NotificationService
from .surge import SurgeService
from .weather import OpenWeatherClient, WeatherReading, WeatherService
from .weather_rules import WeatherChange, detect_change


@dataclass(slots=True)
class WeatherPollResult:
    snapshot: WeatherSnapshot
    change: WeatherChange
    active_surges: int


class AutomationService:
    """Orchestrates weather polling, surge recalculation, and notification fan-out."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        weather_client: OpenWeatherClient | None = None,
        provider: NotificationProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.weather_client = weather_client or OpenWeatherClient(settings)
        self.weather = WeatherService(db, settings)
        self.notifications = NotificationService(
            db, settings, provider or build_provider(settings)
        )
        self.surges = SurgeService(db, settings, self.notifications)

    def poll_weather(self) -> WeatherPollResult:
        reading: WeatherReading = self.weather_client.fetch_current(
            latitude=self.settings.openweather_latitude,
            longitude=self.settings.openweather_longitude,
            city=self.settings.openweather_city,
        )
        previous = self.weather.latest(reading.city)
        change = detect_change(reading, previous, self.settings.weather_max_component)
        snapshot = self.weather.save(reading)

        if change.significant:
            self.notifications.notify_weather(snapshot, change)

        active_surges = self.surges.refresh_all(notify=change.significant)
        return WeatherPollResult(
            snapshot=snapshot,
            change=change,
            active_surges=active_surges,
        )

    def report_accident(
        self,
        *,
        route_id: int,
        description: str,
        severity: str,
        reported_by_user_id: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> tuple[AccidentReport, SurgeEvent | None]:
        route = self.db.get(Route, route_id)
        if route is None:
            raise LookupError(f"Route {route_id} not found")

        report = AccidentReport(
            route_id=route_id,
            reported_by_user_id=reported_by_user_id,
            description=description,
            severity=severity,
            status="reported",
            latitude=latitude,
            longitude=longitude,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        event = self.surges.refresh_route(route, notify=True)
        self.notifications.notify_accident(report, route)
        return report, event

    def update_accident_status(
        self, report_id: int, status: str
    ) -> tuple[AccidentReport, SurgeEvent | None]:
        report = self.db.get(AccidentReport, report_id)
        if report is None:
            raise LookupError(f"Accident report {report_id} not found")

        report.status = status
        if status in {"resolved", "rejected"}:
            report.resolved_at = utcnow()
        self.db.commit()
        self.db.refresh(report)

        route = self.db.get(Route, report.route_id)
        event = self.surges.refresh_route(route, notify=True) if route else None
        return report, event

    def recalculate_surges(self, *, notify: bool = True) -> tuple[int, int]:
        from sqlalchemy import func, select

        routes_evaluated = self.db.scalar(select(func.count()).select_from(Route)) or 0
        active_surges = self.surges.refresh_all(notify=notify)
        return routes_evaluated, active_surges
