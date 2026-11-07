from __future__ import annotations

import re

from sqlalchemy import func, select

import app.routers.auth as auth_module
from app.models import AppUser
from app.providers.base import SendResult

PHONE = "+254742294851"


def test_new_phone_registers_and_can_sign_in(client, db):
    requested = client.post("/api/auth/otp/request", json={"phone": PHONE})
    assert requested.status_code == 200, requested.text
    assert requested.json()["demo"] is True
    assert requested.json()["registered"] is True

    user = db.scalar(select(AppUser).where(AppUser.phone == PHONE))
    assert user is not None

    verified = client.post(
        "/api/auth/otp/verify", json={"phone": PHONE, "code": "4729"}
    )
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["access"]
    assert body["refresh"]
    assert body["user"]["phone"] == PHONE
    assert body["user"]["phone_masked"].endswith("851")

    refreshed = client.post("/api/auth/refresh", json={"refresh": body["refresh"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access"]


def test_existing_phone_is_not_registered_twice(client, db):
    first = client.post("/api/auth/otp/request", json={"phone": PHONE})
    second = client.post("/api/auth/otp/request", json={"phone": "0742294851"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["registered"] is True
    assert second.json()["registered"] is False
    count = db.scalar(select(func.count()).select_from(AppUser).where(AppUser.phone == PHONE))
    assert count == 1


def test_wrong_code_and_bad_phone_are_rejected(client):
    client.post("/api/auth/otp/request", json={"phone": PHONE})
    wrong = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": "0000"})
    assert wrong.status_code == 401

    invalid = client.post("/api/auth/otp/request", json={"phone": "12345"})
    assert invalid.status_code == 422


class FakeSmsProvider:
    name = "thrivewave"

    def __init__(self) -> None:
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return SendResult(success=True, provider_message_id="fake-1")


def test_sms_enabled_sends_a_random_code(client, settings, monkeypatch):
    fake = FakeSmsProvider()
    monkeypatch.setattr(auth_module, "build_provider", lambda _settings: fake)
    monkeypatch.setattr(settings, "sms_enabled", True)

    requested = client.post("/api/auth/otp/request", json={"phone": PHONE})
    assert requested.status_code == 200, requested.text
    assert requested.json()["demo"] is False
    assert len(fake.sent) == 1
    assert fake.sent[0].recipient == PHONE

    match = re.search(r"\b(\d{4})\b", fake.sent[0].body)
    assert match is not None
    code = match.group(1)
    assert code != "4729"

    verified = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": code})
    assert verified.status_code == 200, verified.text
    assert verified.json()["access"]


def test_sms_enabled_requires_a_live_provider(client, settings, monkeypatch):
    class MockProvider:
        name = "mock"

        def send(self, message):  # pragma: no cover - must not be called
            raise AssertionError("mock provider must not be used for OTP SMS")

    monkeypatch.setattr(auth_module, "build_provider", lambda _settings: MockProvider())
    monkeypatch.setattr(settings, "sms_enabled", True)

    response = client.post("/api/auth/otp/request", json={"phone": PHONE})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
