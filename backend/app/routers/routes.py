"""Routes router — Endpoints for querying Mat3Route matatu lines, saccos, and routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.orm import Route, RouteLine, Sacco
from ..models.schemas import (
    PaginatedRoutes,
    RouteInfoOut,
    RouteLineOut,
    RouteOut,
    RouteStatsOut,
    SaccoOut,
)

router = APIRouter(prefix="/routes", tags=["Matatu Routes"])


# ---------------------------------------------------------------------------
# Statistics / Aggregations (Great for Frontend Dashboards)
# ---------------------------------------------------------------------------


@router.get("/stats/summary", response_model=RouteStatsOut, summary="Get summary statistics for dashboard")
async def get_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    """Aggregate statistics for Mat3Route network."""
    total_routes = (await db.execute(select(func.count(Route.id)))).scalar_one() or 0
    total_lines = (await db.execute(select(func.count(RouteLine.id)))).scalar_one() or 0
    total_saccos = (await db.execute(select(func.count(Sacco.id)))).scalar_one() or 0
    min_fare = (await db.execute(select(func.min(Route.fare_min)))).scalar_one() or 0
    max_fare = (await db.execute(select(func.max(Route.fare_max)))).scalar_one() or 0

    top_dest_query = (
        select(Route.end_location, func.count(Route.id).label("count"))
        .group_by(Route.end_location)
        .order_by(desc("count"))
        .limit(5)
    )
    dest_rows = (await db.execute(top_dest_query)).all()
    top_destinations = [{"destination": r[0], "routes": r[1]} for r in dest_rows]

    return RouteStatsOut(
        total_routes=total_routes,
        total_lines=total_lines,
        total_saccos=total_saccos,
        min_fare=min_fare,
        max_fare=max_fare,
        top_destinations=top_destinations,
    )


# ---------------------------------------------------------------------------
# Route Lines
# ---------------------------------------------------------------------------


@router.get("/lines", response_model=list[RouteLineOut], summary="List all route lines")
async def list_lines(db: Annotated[AsyncSession, Depends(get_db)]):
    """Retrieve all Matatu route lines (A Line, B Line, etc.)."""
    result = await db.execute(select(RouteLine).order_by(RouteLine.name))
    return result.scalars().all()


@router.get("/lines/{line_id}", response_model=RouteLineOut, summary="Get a route line by ID")
async def get_line(line_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    obj = await db.get(RouteLine, line_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Route line not found")
    return obj


# ---------------------------------------------------------------------------
# SACCOs
# ---------------------------------------------------------------------------


@router.get("/saccos", response_model=list[SaccoOut], summary="List all SACCOs")
async def list_saccos(db: Annotated[AsyncSession, Depends(get_db)]):
    """Retrieve all transport SACCOs operating across Nairobi routes."""
    result = await db.execute(select(Sacco).order_by(Sacco.name))
    return result.scalars().all()


@router.get("/saccos/{sacco_id}", response_model=SaccoOut, summary="Get a SACCO by ID")
async def get_sacco(sacco_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    obj = await db.get(Sacco, sacco_id)
    if not obj:
        raise HTTPException(status_code=404, detail="SACCO not found")
    return obj


# ---------------------------------------------------------------------------
# Autocomplete / Search helpers
# ---------------------------------------------------------------------------


@router.get("/search/locations", response_model=list[str], summary="Autocomplete locations for React/Angular")
async def search_locations(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query("", description="Partial location search term"),
    field: str = Query("all", description="'start', 'end', or 'all'"),
):
    """Return distinct stages/locations for search autocomplete in UI."""
    results = set()
    if field in ("start", "all"):
        q_start = select(Route.start_location).distinct()
        if q:
            q_start = q_start.where(Route.start_location.ilike(f"%{q}%"))
        start_rows = (await db.execute(q_start.limit(30))).scalars().all()
        results.update(start_rows)

    if field in ("end", "all"):
        q_end = select(Route.end_location).distinct()
        if q:
            q_end = q_end.where(Route.end_location.ilike(f"%{q}%"))
        end_rows = (await db.execute(q_end.limit(30))).scalars().all()
        results.update(end_rows)

    return sorted(list(results))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedRoutes, summary="List routes with filters (for React & Angular tables)")
async def list_routes(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Offset / skip count"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    line: str | None = Query(None, description="Filter by line name (e.g. 'A Line')"),
    sacco_code: str | None = Query(None, description="Filter by SACCO code (e.g. 'SM')"),
    start: str | None = Query(None, description="Filter by departure stage (e.g. 'Nairobi CBD')"),
    end: str | None = Query(None, description="Filter by destination stage (e.g. 'Kiambu')"),
    route_number: str | None = Query(None, description="Filter by route number (e.g. '100')"),
    max_fare: int | None = Query(None, description="Filter by maximum fare (fare_min <= max_fare)"),
    sort_by: str = Query("line", description="'line', 'route_number', 'fare_min', 'fare_max'"),
):
    """Retrieve filtered, paginated matatu routes."""
    stmt = (
        select(
            Route.id,
            RouteLine.name.label("line"),
            Route.route_number,
            Route.start_location.label("start"),
            Route.end_location.label("end"),
            Sacco.name.label("sacco"),
            Sacco.code.label("sacco_code"),
            Route.fare_min,
            Route.fare_max,
        )
        .join(RouteLine, RouteLine.id == Route.line_id)
        .join(Sacco, Sacco.id == Route.sacco_id)
    )

    if line:
        stmt = stmt.where(func.lower(RouteLine.name) == line.lower().strip())
    if sacco_code:
        stmt = stmt.where(func.upper(Sacco.code) == sacco_code.upper().strip())
    if start:
        stmt = stmt.where(Route.start_location.ilike(f"%{start.strip()}%"))
    if end:
        stmt = stmt.where(Route.end_location.ilike(f"%{end.strip()}%"))
    if route_number:
        stmt = stmt.where(Route.route_number == route_number.strip())
    if max_fare is not None:
        stmt = stmt.where(Route.fare_min <= max_fare)

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Ordering
    if sort_by == "fare_min":
        stmt = stmt.order_by(Route.fare_min.asc())
    elif sort_by == "fare_max":
        stmt = stmt.order_by(Route.fare_max.desc())
    elif sort_by == "route_number":
        stmt = stmt.order_by(Route.route_number.asc())
    else:
        stmt = stmt.order_by(RouteLine.name.asc(), Route.route_number.asc())

    rows = (await db.execute(stmt.offset(skip).limit(limit))).mappings().all()
    items = [RouteInfoOut(**row) for row in rows]
    return PaginatedRoutes(total=total, skip=skip, limit=limit, items=items)


@router.get("/{route_id}", response_model=RouteInfoOut, summary="Get a single route by ID")
async def get_route(route_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """Retrieve detailed route data by route ID."""
    stmt = (
        select(
            Route.id,
            RouteLine.name.label("line"),
            Route.route_number,
            Route.start_location.label("start"),
            Route.end_location.label("end"),
            Sacco.name.label("sacco"),
            Sacco.code.label("sacco_code"),
            Route.fare_min,
            Route.fare_max,
        )
        .join(RouteLine, RouteLine.id == Route.line_id)
        .join(Sacco, Sacco.id == Route.sacco_id)
        .where(Route.id == route_id)
    )
    row = (await db.execute(stmt)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")
    return RouteInfoOut(**row)
