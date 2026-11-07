from __future__ import annotations

import logging

from ..config import Settings
from .base import NotificationProvider
from .mock import MockNotificationProvider
from .thrivewave import ThriveWaveProvider

logger = logging.getLogger(__name__)


def build_provider(settings: Settings) -> NotificationProvider:
    provider = getattr(settings, "notification_provider", "mock").lower()
    channel = getattr(settings, "thrivewave_channel", "sms").lower()
    if provider == "thrivewave":
        if channel == "sms" and not getattr(settings, "sms_enabled", False):
            logger.warning(
                "SMS sending is disabled (SMS_ENABLED=false); using the mock provider"
            )
            return MockNotificationProvider()
        if not settings.thrivewave_api_key:
            logger.warning(
                "NOTIFICATION_PROVIDER=thrivewave but THRIVEWAVE_API_KEY is empty; "
                "falling back to the mock provider"
            )
            return MockNotificationProvider()
        return ThriveWaveProvider(settings)
    if provider != "mock":
        logger.warning("Unknown NOTIFICATION_PROVIDER=%r; using mock provider", provider)
    return MockNotificationProvider()
