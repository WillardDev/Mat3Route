from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .providers import build_provider
from .providers.base import NotificationProvider
from .services.automation import AutomationService
from .services.notifications import NotificationService
from .services.surge import SurgeService
from .services.weather import OpenWeatherClient


def get_weather_client(settings: Settings = Depends(get_settings)) -> OpenWeatherClient:
    return OpenWeatherClient(settings)


def get_notification_provider(
    settings: Settings = Depends(get_settings),
) -> NotificationProvider:
    return build_provider(settings)


def get_notification_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: NotificationProvider = Depends(get_notification_provider),
) -> NotificationService:
    return NotificationService(db, settings, provider)


def get_surge_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    notifications: NotificationService = Depends(get_notification_service),
) -> SurgeService:
    return SurgeService(db, settings, notifications)


def get_automation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    weather_client: OpenWeatherClient = Depends(get_weather_client),
    provider: NotificationProvider = Depends(get_notification_provider),
) -> AutomationService:
    return AutomationService(
        db,
        settings,
        weather_client=weather_client,
        provider=provider,
    )


def require_admin(
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_admin_token or not secrets.compare_digest(
        x_admin_token, settings.admin_api_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token",
        )
