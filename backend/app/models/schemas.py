"""Pydantic schemas for request/response serialization."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ── Route Line ────────────────────────────────────────────────────────────────

class RouteLineBase(BaseModel):
    name: str


class RouteLineOut(RouteLineBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ── SACCO ─────────────────────────────────────────────────────────────────────

class SaccoBase(BaseModel):
    name: str
    code: str


class SaccoOut(SaccoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ── Route ─────────────────────────────────────────────────────────────────────

class RouteBase(BaseModel):
    route_number: str
    start_location: str
    end_location: str
    fare_min: int
    fare_max: int


class RouteOut(RouteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    line_id: int
    sacco_id: int
    created_at: datetime
    updated_at: datetime


class RouteInfoOut(BaseModel):
    """Flat view matching the route_info DB view."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    line: str
    route_number: str
    start: str
    end: str
    sacco: str
    sacco_code: str
    fare_min: int
    fare_max: int


# ── Pagination & Aggregations ─────────────────────────────────────────────────

class PaginatedRoutes(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[RouteInfoOut]


class RouteStatsOut(BaseModel):
    total_routes: int
    total_lines: int
    total_saccos: int
    min_fare: int
    max_fare: int
    top_destinations: list[dict[str, str | int]]


# ── ThriveWave SMS ────────────────────────────────────────────────────────────

class SMSCreditsResponse(BaseModel):
    credits: float | int | None = Field(None, description="Available SMS credits on ThriveWave")
    currency: str = "KES"
    status: str = Field(..., description="'active', 'demo', or 'unconfigured'")
    account_id: str | None = None
    rate_per_sms: float = 0.80
    details: dict | None = None


class SMSRequest(BaseModel):
    phone: str = Field(..., description="Recipient phone number (e.g. +254712345678 or 0712345678)")
    message: str = Field(..., max_length=480, description="SMS text content")


class SMSSendRouteRequest(BaseModel):
    phone: str = Field(..., description="Recipient phone number")
    route_id: int = Field(..., description="Database ID of the route")


class SMSResponse(BaseModel):
    success: bool
    message: str
    credits_used: int = 1
    remaining_credits: float | None = None
    recipient: str
    details: dict | None = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    version: str
    db: str
    sms_service: str
