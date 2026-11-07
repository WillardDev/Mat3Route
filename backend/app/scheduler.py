from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from .config import Settings
from .db import SessionLocal
from .providers import build_provider
from .services.automation import AutomationService
from .services.notifications import NotificationService
from .services.surge import SurgeService

logger = logging.getLogger(__name__)


def build_scheduler(settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    first_run = datetime.now(ZoneInfo(settings.timezone)) + timedelta(seconds=10)

    def run_weather_poll() -> None:
        db = SessionLocal()
        try:
            AutomationService(db, settings).poll_weather()
        except Exception:
            logger.exception("scheduled weather poll failed")
            db.rollback()
        finally:
            db.close()

    def run_surge_refresh() -> None:
        db = SessionLocal()
        try:
            AutomationService(db, settings).recalculate_surges(notify=True)
        except Exception:
            logger.exception("scheduled surge refresh failed")
            db.rollback()
        finally:
            db.close()

    def run_surge_expiry() -> None:
        db = SessionLocal()
        try:
            notifications = NotificationService(db, settings, build_provider(settings))
            SurgeService(db, settings, notifications).expire_stale()
        except Exception:
            logger.exception("scheduled surge expiry failed")
            db.rollback()
        finally:
            db.close()

    if settings.openweather_api_key:
        scheduler.add_job(
            run_weather_poll,
            "interval",
            minutes=settings.weather_poll_minutes,
            id="weather_poll",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
            next_run_time=first_run,
        )
    else:
        logger.warning("OPENWEATHER_API_KEY not set; weather polling job is disabled")

    scheduler.add_job(
        run_surge_refresh,
        "interval",
        minutes=settings.surge_refresh_minutes,
        id="surge_refresh",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
        next_run_time=first_run + timedelta(seconds=15),
    )
    scheduler.add_job(
        run_surge_expiry,
        "interval",
        minutes=1,
        id="surge_expiry",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    return scheduler
