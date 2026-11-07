from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_automation_service, get_surge_service, require_admin
from ..models import SurgeEvent
from ..schemas import SurgeOut, SurgeRecalculateOut
from ..services.automation import AutomationService
from ..services.surge import SurgeService

router = APIRouter(prefix="/surges", tags=["surges"])


@router.get("", response_model=list[SurgeOut])
def list_surges(
    route_id: int | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    surges: SurgeService = Depends(get_surge_service),
) -> list[SurgeEvent]:
    if active_only:
        return surges.active_surges(route_id)[offset : offset + limit]

    statement = select(SurgeEvent)
    if route_id is not None:
        statement = statement.where(SurgeEvent.route_id == route_id)
    return list(
        db.scalars(
            statement.order_by(SurgeEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/{surge_id}", response_model=SurgeOut)
def get_surge(surge_id: int, db: Session = Depends(get_db)) -> SurgeEvent:
    event = db.get(SurgeEvent, surge_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Surge event not found")
    return event


@router.post(
    "/recalculate",
    response_model=SurgeRecalculateOut,
    dependencies=[Depends(require_admin)],
)
def recalculate_surges(
    notify: bool = True,
    automation: AutomationService = Depends(get_automation_service),
) -> SurgeRecalculateOut:
    evaluated, active = automation.recalculate_surges(notify=notify)
    return SurgeRecalculateOut(routes_evaluated=evaluated, active_surges=active)


@router.post(
    "/expire",
    dependencies=[Depends(require_admin)],
)
def expire_surges(
    surges: SurgeService = Depends(get_surge_service),
) -> dict:
    expired = surges.expire_stale()
    return {"expired": expired}
