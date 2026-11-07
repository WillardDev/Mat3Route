from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_automation_service, require_admin
from ..models import WeatherSnapshot
from ..schemas import WeatherOut, WeatherRefreshOut
from ..services.automation import AutomationService
from ..services.weather import WeatherError, WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current", response_model=WeatherOut)
def current_weather(
    city: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WeatherSnapshot:
    snapshot = WeatherService(db, settings).latest(city)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No weather snapshot stored yet. Run POST /api/v1/weather/refresh.",
        )
    return snapshot


@router.get("/history", response_model=list[WeatherOut])
def weather_history(
    city: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[WeatherSnapshot]:
    city_name = city or settings.openweather_city
    return list(
        db.scalars(
            select(WeatherSnapshot)
            .where(WeatherSnapshot.city.ilike(city_name))
            .order_by(WeatherSnapshot.observed_at.desc())
            .limit(limit)
        )
    )


@router.post(
    "/refresh",
    response_model=WeatherRefreshOut,
    dependencies=[Depends(require_admin)],
)
def refresh_weather(
    automation: AutomationService = Depends(get_automation_service),
) -> WeatherRefreshOut:
    try:
        result = automation.poll_weather()
    except WeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return WeatherRefreshOut(
        snapshot=result.snapshot,
        significant_change=result.change.significant,
        direction=result.change.direction,
        reason=result.change.reason,
        surge_events_updated=result.active_surges,
    )
