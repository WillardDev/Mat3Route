from __future__ import annotations

from app.config import Settings
from app.models import AppUser, NotificationDevice
from app.providers.base import NotificationMessage, SendResult
from app.services.notifications import NotificationService


class SmsCaptureProvider:
    name = "thrivewave"
    channel = "sms"

    def __init__(self) -> None:
        self.sent: list[NotificationMessage] = []

    def send(self, message: NotificationMessage) -> SendResult:
        self.sent.append(message)
        return SendResult(success=True, provider_message_id="sms-1")


def test_sms_notifications_target_the_user_phone(db, route):
    user = AppUser(phone="+254711111111", name="SMS user", route_id=route.id)
    db.add(user)
    db.flush()
    db.add(
        NotificationDevice(
            user_id=user.id,
            provider="thrivewave",
            token="subscriber-id-not-a-phone",
            platform="web",
        )
    )
    db.commit()

    provider = SmsCaptureProvider()
    service = NotificationService(
        db,
        Settings(database_url="sqlite://", notification_provider="thrivewave"),
        provider,
    )

    service.notify_test(user.id, "Test", "Body")

    assert provider.sent
    assert provider.sent[0].recipient == "+254711111111"
