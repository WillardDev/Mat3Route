from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..dependencies import get_surge_service
from ..models import AppUser, FareQuote, Route
from ..schemas import FareQuoteCreate, FareQuoteOut
from ..services.surge import SurgeService

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("", response_model=FareQuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: FareQuoteCreate,
    db: Session = Depends(get_db),
    surges: SurgeService = Depends(get_surge_service),
) -> FareQuote:
    route = db.scalar(
        select(Route)
        .options(joinedload(Route.line), joinedload(Route.sacco))
        .where(Route.id == payload.route_id)
    )
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if payload.user_id is not None and db.get(AppUser, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    return surges.create_quote(route, user_id=payload.user_id)


@router.get("", response_model=list[FareQuoteOut])
def list_quotes(
    user_id: int | None = None,
    route_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[FareQuote]:
    statement = select(FareQuote)
    if user_id is not None:
        statement = statement.where(FareQuote.user_id == user_id)
    if route_id is not None:
        statement = statement.where(FareQuote.route_id == route_id)
    return list(
        db.scalars(
            statement.order_by(FareQuote.quoted_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/{quote_id}", response_model=FareQuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db)) -> FareQuote:
    quote = db.get(FareQuote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
