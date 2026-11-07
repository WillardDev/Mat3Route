from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class NotificationMessage:
    recipient: str
    title: str
    body: str
    user_id: int | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class NotificationProvider(Protocol):
    name: str

    def send(self, message: NotificationMessage) -> SendResult: ...
