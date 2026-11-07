from __future__ import annotations

import logging
import uuid

from .base import NotificationMessage, SendResult

logger = logging.getLogger(__name__)


class MockNotificationProvider:
    """Local development provider that logs instead of calling an external API."""

    name = "mock"

    def __init__(self) -> None:
        self.sent: list[NotificationMessage] = []

    def send(self, message: NotificationMessage) -> SendResult:
        self.sent.append(message)
        message_id = f"mock-{uuid.uuid4().hex[:12]}"
        logger.info(
            "mock push user=%s recipient=%s title=%r body=%r",
            message.user_id,
            message.recipient,
            message.title,
            message.body,
        )
        return SendResult(success=True, provider_message_id=message_id)
