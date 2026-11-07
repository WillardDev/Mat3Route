from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ..config import Settings
from .base import NotificationMessage, SendResult

logger = logging.getLogger(__name__)


class ThriveWaveProvider:
    """Adapter for ThriveWave notification services.

    Two channels are supported, selected with ``THRIVEWAVE_CHANNEL``:

    ``sms`` (default)
        ThriveVas SMS API. Requests go to
        ``https://sms.thrivevas.com/v1/message/send`` with an ``x-api-key``
        header and a JSON body containing ``message``, ``msisdn`` and
        ``sender_id``.

    ``push``
        ThrivePush personal notifications. Requests use Bearer auth and
        multipart form data with ``website_id``, ``subscriber_id``, ``title``
        and ``description``.
    """

    name = "thrivewave"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def channel(self) -> str:
        return getattr(self.settings, "thrivewave_channel", "sms").lower()

    def send(self, message: NotificationMessage) -> SendResult:
        # Hard stop for SMS: no HTTP request is made while SMS_ENABLED=false.
        if self.channel == "sms" and not getattr(self.settings, "sms_enabled", False):
            logger.warning(
                "SMS sending is disabled (SMS_ENABLED=false); suppressing SMS to %s",
                message.recipient,
            )
            return SendResult(
                success=False,
                error="SMS sending is disabled (SMS_ENABLED=false)",
            )
        try:
            if self.channel == "sms":
                return self._send_sms(message)
            return self._send_push(message)
        except httpx.HTTPError as exc:
            logger.warning("thrivewave delivery failed: %s", exc)
            return SendResult(success=False, error=str(exc))
        except (ValueError, KeyError, TypeError) as exc:
            logger.exception("thrivewave response could not be parsed")
            return SendResult(success=False, error=f"invalid response: {exc}")

    # ------------------------------------------------------------------
    # Web push
    # ------------------------------------------------------------------
    def _send_push(self, message: NotificationMessage) -> SendResult:
        if not self.settings.thrivewave_api_key:
            return SendResult(success=False, error="THRIVEWAVE_API_KEY is not configured")

        url = self.settings.thrivewave_base_url.rstrip("/") + self.settings.thrivewave_notifications_path
        fields = {
            "name": message.title,
            "website_id": self.settings.thrivewave_website_id,
            "subscriber_id": message.recipient,
            "title": message.title,
            "description": message.body,
        }
        if message.data:
            fields["data"] = json.dumps(message.data)

        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {self.settings.thrivewave_api_key}",
                "Accept": "application/json",
            },
            files={key: (None, str(value)) for key, value in fields.items()},
            timeout=self.settings.thrivewave_timeout_seconds,
        )
        response.raise_for_status()
        payload = self._json_or_empty(response)
        return SendResult(
            success=True,
            provider_message_id=self._extract_message_id(payload),
        )

    # ------------------------------------------------------------------
    # ThriveVas SMS
    # ------------------------------------------------------------------
    def _send_sms(self, message: NotificationMessage) -> SendResult:
        # Defence in depth: never reach the network while SMS is disabled.
        if not getattr(self.settings, "sms_enabled", False):
            logger.warning(
                "SMS sending is disabled (SMS_ENABLED=false); suppressing SMS to %s",
                message.recipient,
            )
            return SendResult(
                success=False,
                error="SMS sending is disabled (SMS_ENABLED=false)",
            )
        if not self.settings.thrivewave_api_key:
            return SendResult(success=False, error="THRIVEWAVE_API_KEY is not configured")

        url = self.settings.thrivewave_base_url.rstrip("/") + self.settings.thrivewave_sms_path
        payload: dict[str, Any] = {
            "message": message.body,
            "msisdn": message.recipient,
            "sender_id": self.settings.thrivewave_sender_id or "ThriveVas",
        }
        if self.settings.thrivewave_callback_url:
            payload["callback_url"] = self.settings.thrivewave_callback_url

        response = httpx.post(
            url,
            headers={
                "x-api-key": self.settings.thrivewave_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=self.settings.thrivewave_timeout_seconds,
        )
        response.raise_for_status()
        result = self._json_or_empty(response)
        status = result.get("status")
        if status is not None and str(status) not in {"200", "201", "success", "Success"}:
            return SendResult(
                success=False,
                error=str(result.get("message") or f"ThriveVas error status {status}"),
            )
        return SendResult(
            success=True,
            provider_message_id=self._extract_message_id(result),
        )

    @staticmethod
    def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {}
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _extract_message_id(payload: dict[str, Any]) -> str | None:
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("id", "notification_id", "sms_id", "message_id", "transaction_id"):
                if data.get(key) is not None:
                    return str(data[key])
            sms_ids = data.get("sms_ids")
            if isinstance(sms_ids, list) and sms_ids:
                return str(sms_ids[0])
        for key in ("id", "notification_id", "sms_id", "message_id", "transaction_id"):
            if payload.get(key) is not None:
                return str(payload[key])
        return None
