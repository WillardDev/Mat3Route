"""ThriveWave SMS integration router.

Handles:
- Checking ThriveWave SMS API credits / balance
- Sending SMS notifications with Kenyan number formatting
- Sending route information & fare alerts directly to passengers
"""
import re
from typing import Annotated
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..models.orm import Route, RouteLine, Sacco
from ..models.schemas import (
    SMSCreditsResponse,
    SMSRequest,
    SMSResponse,
    SMSSendRouteRequest,
)

router = APIRouter(prefix="/sms", tags=["ThriveWave SMS"])


def normalize_phone_number(raw_phone: str) -> str:
    """Normalize Kenyan phone numbers to E.164 format (+254...)."""
    phone = re.sub(r"[\s\-\(\)]", "", raw_phone.strip())
    if phone.startswith("+"):
        return phone
    if phone.startswith("0") and len(phone) == 10:
        return f"+254{phone[1:]}"
    if phone.startswith("254") and len(phone) == 12:
        return f"+{phone}"
    if len(phone) == 9 and phone.startswith(("7", "1")):
        return f"+254{phone}"
    return phone


async def _fetch_thrivewave_credits(settings: Settings) -> dict:
    """Fetch SMS credits balance from ThriveWave API."""
    if not settings.thrivewave_api_key:
        return {
            "status": "unconfigured",
            "credits": 500,  # Demo simulated balance for development
            "message": "THRIVEWAVE_API_KEY not set. Operating in simulated demo mode.",
            "currency": "KES",
        }

    headers = {
        "Authorization": f"Bearer {settings.thrivewave_api_key}",
        "x-api-key": settings.thrivewave_api_key,
        "Accept": "application/json",
    }

    url = f"{settings.thrivewave_api_url.rstrip('/')}/credits"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"status": "active", "data": data}
            # Fallback balance endpoint check
            url_alt = f"{settings.thrivewave_api_url.rstrip('/')}/balance"
            resp_alt = await client.get(url_alt, headers=headers)
            if resp_alt.status_code == 200:
                return {"status": "active", "data": resp_alt.json()}
            return {
                "status": "error",
                "code": resp.status_code,
                "detail": resp.text,
            }
        except Exception as exc:
            return {"status": "connection_error", "error": str(exc)}


async def _send_sms_thrivewave(phone: str, message: str, settings: Settings) -> dict:
    """Dispatch SMS via ThriveWave gateway."""
    normalized_phone = normalize_phone_number(phone)

    # Master kill switch: never contact ThriveVas while SMS is disabled.
    if not getattr(settings, "sms_enabled", False):
        return {
            "status": "disabled",
            "recipient": normalized_phone,
            "message": message,
            "cost_credits": 0,
            "simulated": True,
            "note": "SMS sending is disabled (SMS_ENABLED=false).",
        }

    # In demo mode if key not set
    if not settings.thrivewave_api_key:
        return {
            "status": "simulated",
            "recipient": normalized_phone,
            "message": message,
            "cost_credits": 1,
            "simulated": True,
            "note": "SMS simulated successfully. Set THRIVEWAVE_API_KEY for live delivery.",
        }

    headers = {
        "Authorization": f"Bearer {settings.thrivewave_api_key}",
        "x-api-key": settings.thrivewave_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "api_key": settings.thrivewave_api_key,
        "sender_id": settings.thrivewave_sender_id,
        "recipient": normalized_phone,
        "phone": normalized_phone,
        "message": message,
    }

    send_url = f"{settings.thrivewave_api_url.rstrip('/')}/sms/send"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(send_url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                return resp.json()
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"ThriveWave error ({resp.status_code}): {resp.text}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach ThriveWave gateway: {exc}")


@router.get("/credits", response_model=SMSCreditsResponse, summary="Check ThriveWave SMS API credits")
async def get_sms_credits(settings: Annotated[Settings, Depends(get_settings)]):
    """Retrieve available SMS credits and balance on ThriveWave."""
    result = await _fetch_thrivewave_credits(settings)

    if result.get("status") == "unconfigured":
        return SMSCreditsResponse(
            credits=500,
            currency="KES",
            status="demo",
            rate_per_sms=0.80,
            details={
                "info": "Demo simulation. Set THRIVEWAVE_API_KEY environment variable to link live ThriveWave account.",
            },
        )

    if result.get("status") == "active":
        data = result.get("data", {})
        credits_val = data.get("credits") or data.get("balance") or data.get("units")
        return SMSCreditsResponse(
            credits=credits_val,
            currency=data.get("currency", "KES"),
            status="active",
            account_id=str(data.get("account_id", "")),
            rate_per_sms=float(data.get("rate_per_sms", 0.80)),
            details=data,
        )

    return SMSCreditsResponse(
        credits=None,
        currency="KES",
        status=result.get("status", "error"),
        details=result,
    )


@router.post("/send", response_model=SMSResponse, summary="Send custom SMS via ThriveWave")
async def send_sms(
    body: SMSRequest,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Send arbitrary SMS text (e.g. notifications, alerts, directions) via ThriveWave."""
    phone = normalize_phone_number(body.phone)
    res = await _send_sms_thrivewave(phone, body.message, settings)
    disabled = res.get("status") == "disabled"
    return SMSResponse(
        success=not disabled,
        message=(
            "SMS sending is disabled (SMS_ENABLED=false)"
            if disabled
            else "SMS dispatched successfully"
        ),
        credits_used=0 if disabled else 1,
        recipient=phone,
        details=res,
    )


@router.post(
    "/send-route",
    response_model=SMSResponse,
    summary="Send route and fare details to passenger phone via ThriveWave",
)
async def send_route_sms(
    body: SMSSendRouteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Fetch matatu route details from the DB and send as an SMS to the user's phone."""
    phone = normalize_phone_number(body.phone)
    stmt = (
        select(
            Route.route_number,
            Route.start_location,
            Route.end_location,
            Route.fare_min,
            Route.fare_max,
            RouteLine.name.label("line"),
            Sacco.name.label("sacco"),
        )
        .join(RouteLine, RouteLine.id == Route.line_id)
        .join(Sacco, Sacco.id == Route.sacco_id)
        .where(Route.id == body.route_id)
    )
    row = (await db.execute(stmt)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")

    sms_text = (
        f"Mat3Route Guide:\n"
        f"Route: {row['route_number']} ({row['line']})\n"
        f"From: {row['start_location']} -> To: {row['end_location']}\n"
        f"Operator: {row['sacco']}\n"
        f"Fare Range: KES {row['fare_min']} - {row['fare_max']}\n"
        f"Safe travels!"
    )

    result = await _send_sms_thrivewave(phone, sms_text, settings)
    disabled = result.get("status") == "disabled"
    return SMSResponse(
        success=not disabled,
        message=(
            "SMS sending is disabled (SMS_ENABLED=false)"
            if disabled
            else f"Route {row['route_number']} details sent to {phone}"
        ),
        credits_used=0 if disabled else 1,
        recipient=phone,
        details=result,
    )


@router.get("/pricing", summary="Get SMS credits pricing and bundle tiers")
async def get_sms_pricing():
    """Information on ThriveWave SMS credit rates for Mat3Route users."""
    return {
        "provider": "ThriveWave (ThriveVas)",
        "currency": "KES",
        "standard_sms_rate": 0.80,
        "character_limit_per_credit": 160,
        "packages": [
            {"tier": "Starter", "credits": 500, "price": 400, "rate": 0.80},
            {"tier": "Growth", "credits": 2500, "price": 1750, "rate": 0.70},
            {"tier": "Business", "credits": 10000, "price": 6000, "rate": 0.60},
        ],
        "supported_networks": ["Safaricom", "Airtel Kenya", "Telkom Kenya"],
    }
