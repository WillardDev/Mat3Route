from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_automation_service, require_admin
from ..models import AccidentReport, AppUser, Route
from ..schemas import AccidentCreate, AccidentOut, AccidentStatusUpdate
from ..services.automation import AutomationService

router = APIRouter(prefix="/accidents", tags=["accidents"])


@router.post("", response_model=AccidentOut, status_code=status.HTTP_201_CREATED)
def report_accident(
    payload: AccidentCreate,
    db: Session = Depends(get_db),
    automation: AutomationService = Depends(get_automation_service),
) -> AccidentReport:
    if db.get(Route, payload.route_id) is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if payload.reported_by_user_id is not None and db.get(
        AppUser, payload.reported_by_user_id
    ) is None:
        raise HTTPException(status_code=404, detail="Reporting user not found")

    report, _ = automation.report_accident(
        route_id=payload.route_id,
        description=payload.description,
        severity=payload.severity,
        reported_by_user_id=payload.reported_by_user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return report


@router.get("", response_model=list[AccidentOut])
def list_accidents(
    route_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AccidentReport]:
    statement = select(AccidentReport)
    if route_id is not None:
        statement = statement.where(AccidentReport.route_id == route_id)
    if status_filter:
        statement = statement.where(AccidentReport.status == status_filter)
    return list(
        db.scalars(
            statement.order_by(AccidentReport.reported_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/{report_id}", response_model=AccidentOut)
def get_accident(report_id: int, db: Session = Depends(get_db)) -> AccidentReport:
    report = db.get(AccidentReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Accident report not found")
    return report


@router.patch(
    "/{report_id}/status",
    response_model=AccidentOut,
    dependencies=[Depends(require_admin)],
)
def update_accident_status(
    report_id: int,
    payload: AccidentStatusUpdate,
    automation: AutomationService = Depends(get_automation_service),
) -> AccidentReport:
    try:
        report, _ = automation.update_accident_status(report_id, payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return report
