from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..dependencies import get_surge_service
from ..models import Route, RouteLine
from ..schemas import FarePreviewOut, RouteOut
from ..services.surge import SurgeService
from .serializers import serialize_route

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=list[RouteOut])
def list_routes(
    line: str | None = None,
    start: str | None = None,
    end: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(Route).options(
        joinedload(Route.line), joinedload(Route.sacco)
    )

    if line:
        statement = statement.where(Route.line.has(RouteLine.name.ilike(f"%{line}%")))
    if start:
        statement = statement.where(Route.start_location.ilike(f"%{start}%"))
    if end:
        statement = statement.where(Route.end_location.ilike(f"%{end}%"))
    if q:
        like = f"%{q}%"
        statement = statement.where(
            or_(
                Route.route_number.ilike(like),
                Route.start_location.ilike(like),
                Route.end_location.ilike(like),
            )
        )

    routes = db.scalars(
        statement.order_by(Route.line_id, Route.route_number).limit(limit).offset(offset)
    ).unique()
    return [serialize_route(route) for route in routes]


@router.get("/{route_id}", response_model=RouteOut)
def get_route(route_id: int, db: Session = Depends(get_db)) -> dict:
    route = db.scalar(
        select(Route)
        .options(joinedload(Route.line), joinedload(Route.sacco))
        .where(Route.id == route_id)
    )
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return serialize_route(route)


@router.get("/{route_id}/fare", response_model=FarePreviewOut)
def get_route_fare(
    route_id: int,
    db: Session = Depends(get_db),
    surges: SurgeService = Depends(get_surge_service),
) -> dict:
    route = db.scalar(
        select(Route)
        .options(joinedload(Route.line), joinedload(Route.sacco))
        .where(Route.id == route_id)
    )
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return surges.preview(route)
