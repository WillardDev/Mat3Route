from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..dependencies import get_surge_service
from ..models import Route, RouteLine, Sacco
from ..models.schemas import RouteLineOut, RouteStatsOut, SaccoOut
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


@router.get("/stats/summary", response_model=RouteStatsOut, summary="Get summary statistics")
def get_stats(db: Session = Depends(get_db)) -> RouteStatsOut:
    """Aggregate statistics for the Mat3Route network."""
    total_routes = db.scalar(select(func.count(Route.id))) or 0
    total_lines = db.scalar(select(func.count(RouteLine.id))) or 0
    total_saccos = db.scalar(select(func.count(Sacco.id))) or 0
    min_fare = db.scalar(select(func.min(Route.fare_min))) or 0
    max_fare = db.scalar(select(func.max(Route.fare_max))) or 0

    rows = db.execute(
        select(Route.end_location, func.count(Route.id).label("count"))
        .group_by(Route.end_location)
        .order_by(desc("count"))
        .limit(5)
    ).all()
    return RouteStatsOut(
        total_routes=total_routes,
        total_lines=total_lines,
        total_saccos=total_saccos,
        min_fare=min_fare,
        max_fare=max_fare,
        top_destinations=[
            {"destination": destination, "routes": count} for destination, count in rows
        ],
    )


@router.get("/lines", response_model=list[RouteLineOut], summary="List all route lines")
def list_lines(db: Session = Depends(get_db)) -> list[RouteLine]:
    return list(db.scalars(select(RouteLine).order_by(RouteLine.name)))


@router.get("/lines/{line_id}", response_model=RouteLineOut, summary="Get a route line by ID")
def get_line(line_id: int, db: Session = Depends(get_db)) -> RouteLine:
    line = db.get(RouteLine, line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Route line not found")
    return line


@router.get("/saccos", response_model=list[SaccoOut], summary="List all SACCOs")
def list_saccos(db: Session = Depends(get_db)) -> list[Sacco]:
    return list(db.scalars(select(Sacco).order_by(Sacco.name)))


@router.get("/saccos/{sacco_id}", response_model=SaccoOut, summary="Get a SACCO by ID")
def get_sacco(sacco_id: int, db: Session = Depends(get_db)) -> Sacco:
    sacco = db.get(Sacco, sacco_id)
    if sacco is None:
        raise HTTPException(status_code=404, detail="SACCO not found")
    return sacco


@router.get(
    "/search/locations",
    response_model=list[str],
    summary="Autocomplete locations for the frontend",
)
def search_locations(
    db: Session = Depends(get_db),
    q: str = Query(default="", description="Partial location search term"),
    field: str = Query(default="all", description="'start', 'end', or 'all'"),
) -> list[str]:
    results: set[str] = set()
    if field in ("start", "all"):
        statement = select(Route.start_location).distinct()
        if q:
            statement = statement.where(Route.start_location.ilike(f"%{q}%"))
        results.update(db.scalars(statement.limit(30)))
    if field in ("end", "all"):
        statement = select(Route.end_location).distinct()
        if q:
            statement = statement.where(Route.end_location.ilike(f"%{q}%"))
        results.update(db.scalars(statement.limit(30)))
    return sorted(results)


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
