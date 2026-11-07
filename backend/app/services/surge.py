from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import Settings
from ..models import AccidentReport, FareQuote, Route, SurgeEvent, WeatherSnapshot
from ..utils import ensure_utc, utcnow
from .fare_rules import accident_component, apply_multiplier, peak_component
from .notifications import NotificationService
from .weather_rules import assess

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SurgeComputation:
    multiplier: float
    weather_component: float
    accident_component: float
    peak_component: float
    trigger_type: str
    reasons: list[str]
    base_fare_min: int
    base_fare_max: int
    fare_min: int
    fare_max: int
    weather_snapshot_id: int | None
    accident_report_id: int | None


class SurgeService:
    def __init__(self, db: Session, settings: Settings, notifications: NotificationService) -> None:
        self.db = db
        self.settings = settings
        self.notifications = notifications

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    def compute(self, route: Route, now: datetime | None = None) -> SurgeComputation:
        now = ensure_utc(now or utcnow())

        weather = self.db.scalar(
            select(WeatherSnapshot)
            .order_by(WeatherSnapshot.observed_at.desc(), WeatherSnapshot.id.desc())
            .limit(1)
        )
        weather_assessment = assess(weather, self.settings.weather_max_component) if weather else None
        weather_component = weather_assessment.component if weather_assessment else 0.0

        reports = self._active_accident_reports(route.id, now)
        accident_comp = accident_component(reports, self.settings.accident_max_component)
        peak_comp, peak_label = peak_component(
            now,
            self.settings.timezone,
            self.settings.peak_morning_component,
            self.settings.peak_evening_component,
        )

        raw_multiplier = 1.0 + weather_component + accident_comp + peak_comp
        multiplier = round(min(raw_multiplier, self.settings.max_surge_multiplier), 2)
        fare_min, fare_max = apply_multiplier(route.fare_min, route.fare_max, multiplier)

        reasons: list[str] = []
        if weather_assessment and weather_component > 0:
            reasons.append(f"{weather_assessment.label} weather")
        if reports and accident_comp > 0:
            severities = sorted({report.severity for report in reports})
            reasons.append(
                f"{len(reports)} active {', '.join(severities)} accident report"
                f"{'s' if len(reports) != 1 else ''}"
            )
        if peak_label:
            reasons.append(peak_label)
        if raw_multiplier > self.settings.max_surge_multiplier:
            reasons.append("maximum surge cap applied")

        active_triggers = [
            name
            for name, value in (
                ("weather", weather_component),
                ("accident", accident_comp),
                ("peak_hour", peak_comp),
            )
            if value > 0
        ]
        if len(active_triggers) > 1:
            trigger_type = "combined"
        elif active_triggers:
            trigger_type = active_triggers[0]
        else:
            trigger_type = "manual"

        return SurgeComputation(
            multiplier=multiplier,
            weather_component=weather_component,
            accident_component=accident_comp,
            peak_component=peak_comp,
            trigger_type=trigger_type,
            reasons=reasons or ["normal conditions"],
            base_fare_min=route.fare_min,
            base_fare_max=route.fare_max,
            fare_min=fare_min,
            fare_max=fare_max,
            weather_snapshot_id=weather.id if weather else None,
            accident_report_id=reports[0].id if reports else None,
        )

    def _active_accident_reports(self, route_id: int, now: datetime) -> list[AccidentReport]:
        cutoff = now - timedelta(minutes=self.settings.accident_lookback_minutes)
        return list(
            self.db.scalars(
                select(AccidentReport)
                .where(
                    AccidentReport.route_id == route_id,
                    AccidentReport.status.in_(("reported", "verified")),
                    AccidentReport.reported_at >= cutoff,
                )
                .order_by(AccidentReport.reported_at.desc())
            )
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def refresh_route(
        self,
        route: Route,
        *,
        notify: bool = True,
        now: datetime | None = None,
        force_notify: bool = False,
    ) -> SurgeEvent | None:
        now = ensure_utc(now or utcnow())
        active = list(
            self.db.scalars(
                select(SurgeEvent).where(
                    SurgeEvent.route_id == route.id,
                    SurgeEvent.is_active.is_(True),
                )
            )
        )
        previous = max(active, key=lambda event: event.multiplier) if active else None
        calc = self.compute(route, now)
        ends_at = now + timedelta(minutes=self.settings.surge_ttl_minutes)

        reusable = (
            previous
            if previous
            and previous.trigger_type == calc.trigger_type
            and abs(previous.multiplier - calc.multiplier) < 0.05
            else None
        )

        event: SurgeEvent | None = None
        changed = False

        if reusable is not None:
            event = reusable
            event.multiplier = calc.multiplier
            event.weather_component = calc.weather_component
            event.accident_component = calc.accident_component
            event.peak_component = calc.peak_component
            event.base_fare_min = calc.base_fare_min
            event.base_fare_max = calc.base_fare_max
            event.adjusted_fare_min = calc.fare_min
            event.adjusted_fare_max = calc.fare_max
            event.reason = "; ".join(calc.reasons)
            event.ends_at = ends_at
            event.updated_at = now
            event.weather_snapshot_id = calc.weather_snapshot_id
            event.accident_report_id = calc.accident_report_id
            event.is_active = True
            for other in active:
                if other is not event:
                    other.is_active = False
            changed = abs(previous.multiplier - calc.multiplier) >= 0.05 if previous else False
        elif calc.multiplier > 1.005:
            for stale in active:
                stale.is_active = False
            self.db.flush()
            event = SurgeEvent(
                route_id=route.id,
                trigger_type=calc.trigger_type,
                multiplier=calc.multiplier,
                weather_component=calc.weather_component,
                accident_component=calc.accident_component,
                peak_component=calc.peak_component,
                base_fare_min=calc.base_fare_min,
                base_fare_max=calc.base_fare_max,
                adjusted_fare_min=calc.fare_min,
                adjusted_fare_max=calc.fare_max,
                reason="; ".join(calc.reasons),
                starts_at=now,
                ends_at=ends_at,
                is_active=True,
                weather_snapshot_id=calc.weather_snapshot_id,
                accident_report_id=calc.accident_report_id,
            )
            self.db.add(event)
            changed = True
        else:
            for stale in active:
                stale.is_active = False
            changed = bool(active)

        self.db.commit()

        if event is not None:
            self.db.refresh(event)
            if notify and (force_notify or changed or previous is None):
                self.notifications.notify_surge(event, route)
        return event

    def ensure_current(
        self, route: Route, now: datetime | None = None
    ) -> SurgeEvent | None:
        now = ensure_utc(now or utcnow())
        active = self.db.scalar(
            select(SurgeEvent)
            .where(
                SurgeEvent.route_id == route.id,
                SurgeEvent.is_active.is_(True),
                SurgeEvent.ends_at > now,
            )
            .order_by(SurgeEvent.multiplier.desc())
            .limit(1)
        )
        if active is not None:
            age = now - ensure_utc(active.updated_at)
            if age <= timedelta(minutes=self.settings.surge_refresh_minutes):
                return active
        return self.refresh_route(route, notify=False, now=now)

    def refresh_all(
        self, *, notify: bool = True, now: datetime | None = None
    ) -> int:
        now = ensure_utc(now or utcnow())
        routes = list(
            self.db.scalars(
                select(Route).options(joinedload(Route.line), joinedload(Route.sacco))
            )
        )
        active_count = 0
        for route in routes:
            event = self.refresh_route(route, notify=notify, now=now)
            if event is not None:
                active_count += 1
        return active_count

    def expire_stale(self, now: datetime | None = None) -> int:
        now = ensure_utc(now or utcnow())
        stale = list(
            self.db.scalars(
                select(SurgeEvent).where(
                    SurgeEvent.is_active.is_(True),
                    SurgeEvent.ends_at < now,
                )
            )
        )
        for event in stale:
            event.is_active = False
        if stale:
            self.db.commit()
        return len(stale)

    def active_surges(self, route_id: int | None = None) -> list[SurgeEvent]:
        now = utcnow()
        statement = select(SurgeEvent).where(
            SurgeEvent.is_active.is_(True),
            SurgeEvent.ends_at > now,
        )
        if route_id is not None:
            statement = statement.where(SurgeEvent.route_id == route_id)
        return list(
            self.db.scalars(
                statement.order_by(SurgeEvent.multiplier.desc(), SurgeEvent.id.desc())
            )
        )

    # ------------------------------------------------------------------
    # Fare previews and quotes
    # ------------------------------------------------------------------
    def preview(self, route: Route, now: datetime | None = None) -> dict[str, Any]:
        now = ensure_utc(now or utcnow())
        event = self.ensure_current(route, now)
        calc = self.compute(route, now)

        if event is not None:
            fare_min = event.adjusted_fare_min
            fare_max = event.adjusted_fare_max
            multiplier = event.multiplier
            components = {
                "weather": event.weather_component,
                "accident": event.accident_component,
                "peak_hour": event.peak_component,
            }
            reasons = [reason.strip() for reason in event.reason.split(";") if reason.strip()]
            event_id = event.id
            ends_at = event.ends_at
            active = True
        else:
            fare_min, fare_max = route.fare_min, route.fare_max
            multiplier = 1.0
            components = {
                "weather": calc.weather_component,
                "accident": calc.accident_component,
                "peak_hour": calc.peak_component,
            }
            reasons = calc.reasons
            event_id = None
            ends_at = None
            active = False

        return {
            "route_id": route.id,
            "line": route.line.name,
            "route_number": route.route_number,
            "start": route.start_location,
            "end": route.end_location,
            "base_fare_min": route.fare_min,
            "base_fare_max": route.fare_max,
            "fare_min": fare_min,
            "fare_max": fare_max,
            "multiplier": multiplier,
            "components": components,
            "reasons": reasons,
            "surge_event_id": event_id,
            "surge_ends_at": ends_at,
            "active": active,
        }

    def create_quote(
        self,
        route: Route,
        *,
        user_id: int | None = None,
        now: datetime | None = None,
    ) -> FareQuote:
        now = ensure_utc(now or utcnow())
        preview = self.preview(route, now)
        quote = FareQuote(
            user_id=user_id,
            route_id=route.id,
            surge_event_id=preview["surge_event_id"],
            multiplier=preview["multiplier"],
            base_fare_min=preview["base_fare_min"],
            base_fare_max=preview["base_fare_max"],
            fare_min=preview["fare_min"],
            fare_max=preview["fare_max"],
            quoted_at=now,
            expires_at=now + timedelta(minutes=self.settings.quote_ttl_minutes),
        )
        self.db.add(quote)
        self.db.commit()
        self.db.refresh(quote)
        return quote
