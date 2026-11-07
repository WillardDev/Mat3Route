from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings
from ..models import (
    AccidentReport,
    AppUser,
    Notification,
    Route,
    SurgeEvent,
    WeatherSnapshot,
)
from ..providers.base import NotificationMessage, NotificationProvider
from ..utils import ensure_utc, utcnow
from .weather_rules import WeatherChange

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session, settings: Settings, provider: NotificationProvider) -> None:
        self.db = db
        self.settings = settings
        self.provider = provider

    # ------------------------------------------------------------------
    # Public notification types
    # ------------------------------------------------------------------
    def notify_weather(self, snapshot: WeatherSnapshot, change: WeatherChange) -> int:
        users = self._users_in_city(snapshot.city)
        if change.direction == "improved":
            title = f"Weather easing in {snapshot.city}"
            body = (
                f"{change.reason or 'Weather conditions are improving'}. "
                "Fare surcharges are being reviewed and may reduce."
            )
        else:
            label = change.label or snapshot.description
            title = f"Weather alert: {label} in {snapshot.city}"
            body = (
                f"{change.reason or f'Conditions changed to {label}'}. "
                "Fares may rise on affected routes. Book early to lock in the current fare."
            )

        payload = {
            "kind": "weather",
            "city": snapshot.city,
            "condition": snapshot.condition_main,
            "description": snapshot.description,
            "temperature_c": snapshot.temperature_c,
            "observed_at": snapshot.observed_at.isoformat(),
        }
        return self._dispatch(
            users,
            notification_type="weather",
            title=title,
            body=body,
            dedupe_key_fn=lambda user: f"weather:{snapshot.id}:{user.id}",
            weather_snapshot_id=snapshot.id,
            payload=payload,
        )

    def notify_surge(self, event: SurgeEvent, route: Route) -> int:
        users = self._users_for_route(route.id)
        title = f"Fare update: {route.route_number} {route.start_location} to {route.end_location}"
        body = (
            f"Fares are now KSh {event.adjusted_fare_min}-{event.adjusted_fare_max} "
            f"(base KSh {event.base_fare_min}-{event.base_fare_max}) due to {event.reason}. "
            f"Quote valid for {self.settings.quote_ttl_minutes} minutes."
        )
        event_hour = ensure_utc(event.starts_at).strftime("%Y%m%d%H")
        payload = {
            "kind": "surge",
            "route_id": route.id,
            "route_number": route.route_number,
            "multiplier": event.multiplier,
            "fare_min": event.adjusted_fare_min,
            "fare_max": event.adjusted_fare_max,
            "ends_at": event.ends_at.isoformat(),
        }
        return self._dispatch(
            users,
            notification_type="surge",
            title=title,
            body=body,
            dedupe_key_fn=lambda user: (
                f"surge:{route.id}:{event.multiplier:.2f}:{user.id}:{event_hour}"
            ),
            surge_event_id=event.id,
            payload=payload,
        )

    def notify_accident(self, report: AccidentReport, route: Route) -> int:
        users = self._users_for_route(route.id)
        title = f"Route disruption: {route.route_number}"
        body = (
            f"A {report.severity} accident was reported on "
            f"{route.start_location} to {route.end_location}. "
            f"{report.description}. Fares may change while the route is disrupted."
        )
        payload = {
            "kind": "accident",
            "route_id": route.id,
            "route_number": route.route_number,
            "severity": report.severity,
            "report_id": report.id,
        }
        return self._dispatch(
            users,
            notification_type="accident",
            title=title,
            body=body,
            dedupe_key_fn=lambda user: f"accident:{report.id}:{user.id}",
            accident_report_id=report.id,
            payload=payload,
        )

    def notify_test(self, user_id: int, title: str, body: str) -> Notification | None:
        user = self.db.get(AppUser, user_id)
        if user is None:
            return None
        self._dispatch(
            [user],
            notification_type="system",
            title=title,
            body=body,
            dedupe_key_fn=None,
            payload={"kind": "system"},
        )
        return self.db.scalar(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.id.desc())
            .limit(1)
        )

    def list_for_user(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Notification]:
        return list(
            self.db.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _users_in_city(self, city: str) -> list[AppUser]:
        return list(
            self.db.scalars(
                select(AppUser)
                .options(selectinload(AppUser.devices))
                .where(
                    AppUser.is_active.is_(True),
                    func.lower(AppUser.city) == city.lower(),
                )
                .order_by(AppUser.id)
                .limit(self.settings.notification_batch_size)
            )
        )

    def _users_for_route(self, route_id: int) -> list[AppUser]:
        return list(
            self.db.scalars(
                select(AppUser)
                .options(selectinload(AppUser.devices))
                .where(
                    AppUser.is_active.is_(True),
                    AppUser.route_id == route_id,
                )
                .order_by(AppUser.id)
                .limit(self.settings.notification_batch_size)
            )
        )

    def _recipient_for(self, user: AppUser, device) -> str:
        """SMS providers need a phone number; push providers use the device token."""
        if getattr(self.provider, "channel", "") == "sms":
            return user.phone
        return device.token

    def _dispatch(
        self,
        users: list[AppUser],
        *,
        notification_type: str,
        title: str,
        body: str,
        dedupe_key_fn,
        weather_snapshot_id: int | None = None,
        surge_event_id: int | None = None,
        accident_report_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        delivered = 0
        for user in users:
            dedupe_key = dedupe_key_fn(user) if dedupe_key_fn else None
            if dedupe_key and self.db.scalar(
                select(Notification.id).where(Notification.dedupe_key == dedupe_key)
            ):
                continue

            notification = Notification(
                user_id=user.id,
                notification_type=notification_type,
                title=title,
                body=body,
                provider=self.provider.name,
                status="pending",
                dedupe_key=dedupe_key,
                weather_snapshot_id=weather_snapshot_id,
                surge_event_id=surge_event_id,
                accident_report_id=accident_report_id,
                payload=payload,
            )
            self.db.add(notification)

            devices = [device for device in user.devices if device.is_active]
            if not devices:
                notification.status = "skipped"
                notification.error = "No active notification devices"
                self.db.commit()
                continue

            successes = 0
            errors: list[str] = []
            provider_message_id: str | None = None
            for device in devices:
                try:
                    result = self.provider.send(
                        NotificationMessage(
                            recipient=self._recipient_for(user, device),
                            title=title,
                            body=body,
                            user_id=user.id,
                            data=payload or {},
                        )
                    )
                except Exception as exc:  # keep one bad device from blocking a batch
                    logger.exception("notification provider raised for user=%s", user.id)
                    errors.append(str(exc))
                    continue

                if result.success:
                    successes += 1
                    provider_message_id = result.provider_message_id or provider_message_id
                else:
                    errors.append(result.error or "unknown delivery error")

            if successes:
                notification.status = "sent"
                notification.sent_at = utcnow()
                notification.provider_message_id = provider_message_id
                delivered += 1
            else:
                notification.status = "failed"
                notification.error = "; ".join(errors)[:2000] or "delivery failed"

            self.db.commit()

        return delivered
