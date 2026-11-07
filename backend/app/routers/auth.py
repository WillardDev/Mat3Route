"""Phone-number OTP authentication for the MatatuPulse frontend.

New phone numbers are registered automatically: the only field required is the
phone number. While ``SMS_ENABLED=false`` no SMS is sent and the demo code
(``DEMO_OTP_CODE``, default ``4729``) is accepted. With SMS enabled a fresh
4-digit code is generated and delivered through ThriveVas.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import AppUser
from ..providers import build_provider
from ..providers.base import NotificationMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# phone -> (code, expires_at)
_otp_store: dict[str, tuple[str, float]] = {}


class OtpRequest(BaseModel):
    phone: str = Field(..., description="Phone number in +254… or 07… format")


class OtpVerify(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=8)


class RefreshRequest(BaseModel):
    refresh: str


def normalize_phone(raw: str) -> str:
    phone = re.sub(r"[\s\-\(\)]", "", (raw or "").strip())
    if phone.startswith("+"):
        return phone
    if phone.startswith("0") and len(phone) == 10:
        return f"+254{phone[1:]}"
    if phone.startswith("254") and len(phone) == 12:
        return f"+{phone}"
    if len(phone) == 9 and phone.startswith(("7", "1")):
        return f"+254{phone}"
    return phone


def mask_phone(phone: str) -> str:
    digits = phone.lstrip("+")
    if digits.startswith("254") and len(digits) >= 12:
        local = digits[3:]
        return f"+254 {local[:3]} ••• {local[-3:]}"
    if len(phone) > 6:
        return f"{phone[:4]} ••• {phone[-3:]}"
    return phone


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _signature(secret: str, payload: str) -> str:
    return _b64encode(
        hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    )


def _make_token(user_id: int, kind: str, settings: Settings) -> str:
    now = int(time.time())
    ttl = (
        settings.access_token_ttl_minutes * 60
        if kind == "access"
        else settings.refresh_token_ttl_days * 86400
    )
    payload = _b64encode(
        json.dumps(
            {"sub": user_id, "type": kind, "iat": now, "exp": now + ttl},
            separators=(",", ":"),
        ).encode()
    )
    return f"{payload}.{_signature(settings.auth_secret, payload)}"


def _decode_token(token: str, expected: str, settings: Settings) -> int:
    try:
        payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _signature(settings.auth_secret, payload)):
            raise ValueError("bad signature")
        claims = json.loads(_b64decode(payload))
        if claims.get("type") != expected:
            raise ValueError("wrong token type")
        if int(claims.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return int(claims["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def _user_payload(user: AppUser) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "phone_masked": mask_phone(user.phone),
        "is_staff": False,
    }


def _get_or_create_user(db: Session, phone: str) -> tuple[AppUser, bool]:
    user = db.scalar(select(AppUser).where(AppUser.phone == phone))
    if user is not None:
        return user, False

    user = AppUser(phone=phone, city="Nairobi", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("registered new user %s from phone login", user.id)
    return user, True


def _valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"\+254[17]\d{8}", phone))


def _generate_otp() -> str:
    """A 4-digit code without a leading zero (matches the OTP input UI)."""
    return str(secrets.randbelow(9000) + 1000)


def _send_otp_sms(phone: str, code: str, settings: Settings) -> None:
    """Deliver the OTP through the live provider, or fail loudly.

    Logging deliberately never includes the code.
    """
    provider = build_provider(settings)
    if provider.name != "thrivewave":
        logger.error("SMS is enabled but no live ThriveVas provider is configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SMS is not configured. Set NOTIFICATION_PROVIDER=thrivewave "
                "and THRIVEWAVE_API_KEY."
            ),
        )

    result = provider.send(
        NotificationMessage(
            recipient=phone,
            title="Mat3Route login code",
            body=(
                f"Your Mat3Route login code is {code}. "
                f"It expires in {settings.otp_ttl_minutes} minutes."
            ),
        )
    )
    if not result.success:
        logger.error("OTP SMS failed for %s: %s", mask_phone(phone), result.error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="We could not send the SMS. Check the number and try again.",
        )


@router.post("/otp/request")
def request_otp(
    payload: OtpRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Register the number if needed and issue an OTP.

    With ``SMS_ENABLED=false`` the demo code is accepted and shown on screen.
    With SMS enabled a random code is sent to the phone.
    """
    phone = normalize_phone(payload.phone)
    if not _valid_phone(phone):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid Kenyan phone number, e.g. 0712 345 678.",
        )

    user, registered = _get_or_create_user(db, phone)
    demo = not settings.sms_enabled
    code = settings.demo_otp_code if demo else _generate_otp()
    _otp_store[phone] = (
        code,
        time.time() + settings.otp_ttl_minutes * 60,
    )

    if not demo:
        _send_otp_sms(phone, code, settings)

    logger.info(
        "OTP requested for user=%s demo=%s delivered=%s",
        user.id,
        demo,
        not demo,
    )

    return {
        "demo": demo,
        "registered": registered,
        "expires_in": settings.otp_ttl_minutes * 60,
        "message": (
            "Demo mode: use the code shown on screen."
            if demo
            else "We sent you a 4-digit code by SMS."
        ),
    }


@router.post("/otp/verify")
def verify_otp(
    payload: OtpVerify,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    phone = normalize_phone(payload.phone)
    if not _valid_phone(phone):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid Kenyan phone number.",
        )

    stored = _otp_store.get(phone)
    demo_ok = not settings.sms_enabled and payload.code == settings.demo_otp_code
    stored_ok = bool(stored and stored[0] == payload.code and stored[1] >= time.time())
    if not (demo_ok or stored_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That code is incorrect or has expired.",
        )

    _otp_store.pop(phone, None)
    user, _ = _get_or_create_user(db, phone)

    return {
        "access": _make_token(user.id, "access", settings),
        "refresh": _make_token(user.id, "refresh", settings),
        "user": _user_payload(user),
    }


@router.post("/refresh")
def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    user_id = _decode_token(payload.refresh, "refresh", settings)
    user = db.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return {
        "access": _make_token(user.id, "access", settings),
        "refresh": _make_token(user.id, "refresh", settings),
        "user": _user_payload(user),
    }


@router.get("/me")
def me(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str = Header(default=""),
) -> dict:
    """Return the signed-in user for a ``Bearer`` access token."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    user_id = _decode_token(token, "access", settings)
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_payload(user)


def current_user_optional(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str = Header(default=""),
) -> AppUser | None:
    """Resolve a ``Bearer`` token when present; return ``None`` otherwise.

    Used by public endpoints that personalise the response (``my_vote``,
    ``subscribed``) without requiring sign-in.
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        user_id = _decode_token(token, "access", settings)
    except HTTPException:
        return None
    return db.get(AppUser, user_id)


def require_user(user: AppUser | None = Depends(current_user_optional)) -> AppUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
        )
    return user
