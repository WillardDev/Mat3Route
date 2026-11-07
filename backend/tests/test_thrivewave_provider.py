from __future__ import annotations

import httpx

from app.config import Settings
from app.providers.base import NotificationMessage
from app.providers.thrivewave import ThriveWaveProvider


def thrivewave_settings(**overrides) -> Settings:
    values = {
        "database_url": "sqlite://",
        "notification_provider": "thrivewave",
        "sms_enabled": True,
        "thrivewave_api_key": "test-key",
        "thrivewave_channel": "sms",
        "thrivewave_base_url": "https://sms.thrivevas.com",
        "thrivewave_sms_path": "/v1/message/send",
        "thrivewave_sender_id": "ThriveVas",
        "thrivewave_website_id": "17",
        "thrivewave_notifications_path": "/api/personal-notifications",
    }
    values.update(overrides)
    return Settings(**values)


def test_thrivevas_sms_payload_and_message_id(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return httpx.Response(
            200,
            json={"status": 200, "message": "queued", "transaction_id": 98765},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.providers.thrivewave.httpx.post", fake_post)
    provider = ThriveWaveProvider(thrivewave_settings())

    result = provider.send(
        NotificationMessage(
            recipient="+254700000001",
            title="Fare update",
            body="Fares are now KSh 100-140",
            user_id=1,
            data={"route_id": 1},
        )
    )

    assert result.success is True
    assert result.provider_message_id == "98765"
    assert captured["url"] == "https://sms.thrivevas.com/v1/message/send"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert "Authorization" not in captured["headers"]
    assert captured["json"] == {
        "message": "Fares are now KSh 100-140",
        "msisdn": "+254700000001",
        "sender_id": "ThriveVas",
    }


def test_thrivevas_rejects_non_success_status(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return httpx.Response(
            200,
            json={"status": 422, "message": "missing message"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.providers.thrivewave.httpx.post", fake_post)
    provider = ThriveWaveProvider(thrivewave_settings())

    result = provider.send(
        NotificationMessage(recipient="+254700000001", title="Test", body="Test")
    )

    assert result.success is False
    assert "missing message" in (result.error or "")


def test_push_payload_and_message_id(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers, files, timeout):
        captured.update(url=url, headers=headers, files=files, timeout=timeout)
        return httpx.Response(
            200,
            json={"data": {"id": 4321}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.providers.thrivewave.httpx.post", fake_post)
    provider = ThriveWaveProvider(
        thrivewave_settings(
            thrivewave_channel="push",
            thrivewave_base_url="https://thrivepush.example",
        )
    )

    result = provider.send(
        NotificationMessage(
            recipient="subscriber-1",
            title="Fare update",
            body="Fares are now KSh 100-140",
            user_id=1,
            data={"route_id": 1},
        )
    )

    assert result.success is True
    assert result.provider_message_id == "4321"
    assert captured["url"] == "https://thrivepush.example/api/personal-notifications"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["files"]["subscriber_id"] == (None, "subscriber-1")
    assert captured["files"]["website_id"] == (None, "17")


def test_missing_api_key_returns_failure():
    provider = ThriveWaveProvider(thrivewave_settings(thrivewave_api_key=""))
    result = provider.send(
        NotificationMessage(recipient="+254700000001", title="Test", body="Test")
    )
    assert result.success is False
    assert "not configured" in (result.error or "")


def test_sms_is_not_sent_when_disabled(monkeypatch):
    calls: list[object] = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("ThriveVas must not be contacted while SMS is disabled")

    monkeypatch.setattr("app.providers.thrivewave.httpx.post", fake_post)
    provider = ThriveWaveProvider(thrivewave_settings(sms_enabled=False))

    result = provider.send(
        NotificationMessage(recipient="+254700000001", title="Test", body="Test")
    )

    assert result.success is False
    assert "disabled" in (result.error or "")
    assert calls == []
