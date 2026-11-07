from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/")
def root(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "notification_provider": settings.notification_provider,
        "notification_channel": (
            settings.thrivewave_channel.lower()
            if settings.notification_provider.lower() == "thrivewave"
            else "mock"
        ),
        "thrivewave_configured": bool(settings.thrivewave_api_key),
        "weather_configured": bool(settings.openweather_api_key),
        "scheduler_enabled": settings.scheduler_enabled,
    }
