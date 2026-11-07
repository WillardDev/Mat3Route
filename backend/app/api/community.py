"""Commuter-facing API consumed by the MatatuPulse React frontend.

The frontend (``MatatuPulse/frontend/src/api/client.js``) talks to ``/api/*``
rather than ``/api/v1/*`` and uses a slightly richer route shape than the
live-map serializers. This module adapts the existing PostgreSQL models into
that shape and adds the community report/vote/subscribe flow.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..locations import load_locations
from ..models import (
    AccidentReport,
    CommuterEvent,
    CommuterVote,
    Notification,
    Route,
    RouteSubscription,
    Sacco,
    SurgeEvent,
    AppUser,
)
from ..routers.auth import current_user_optional, mask_phone, require_user
from ..utils import ensure_utc, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MatatuPulse"])

VERIFY_AT = 3
HOUR = timedelta(hours=1)

TYPE_LABELS = {
    "fare_hike": "Fare hike",
    "jam": "Jam / Stall",
    "accident_police": "Accident / Police",
    "route_closed": "Route closed",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _natural_key(number: str) -> tuple:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", number or "")
        if part
    )


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat()


def _route_groups(db: Session) -> list[list[Route]]:
    rows = db.scalars(
        select(Route)
        .options(joinedload(Route.line), joinedload(Route.sacco))
        .order_by(Route.id)
    ).all()
    groups: dict[str, list[Route]] = defaultdict(list)
    for route in rows:
        groups[route.route_number].append(route)
    return sorted(groups.values(), key=lambda group: _natural_key(group[0].route_number))


def _group_for_id(db: Session, route_id: int) -> list[Route] | None:
    route = db.get(Route, route_id)
    if route is None:
        return None
    return list(
        db.scalars(
            select(Route)
            .options(joinedload(Route.line), joinedload(Route.sacco))
            .where(Route.route_number == route.route_number)
            .order_by(Route.id)
        ).all()
    )


def _active_events(
    db: Session, route_number: str | None = None, now: datetime | None = None
) -> list[CommuterEvent]:
    now = now or utcnow()
    statement = select(CommuterEvent).where(
        CommuterEvent.status.in_(("pending", "verified")),
        (CommuterEvent.expires_at.is_(None)) | (CommuterEvent.expires_at > now),
    )
    if route_number is not None:
        statement = statement.where(CommuterEvent.route_number == route_number)
    return list(
        db.scalars(statement.order_by(CommuterEvent.last_seen.desc(), CommuterEvent.id.desc())).all()
    )


def _event_label(kind: str, subtype: str | None) -> str:
    if kind == "accident_police":
        return "Police check" if subtype == "police" else "Accident"
    return TYPE_LABELS.get(kind, kind.replace("_", " ").title())


def _event_dict(event: CommuterEvent, my_vote: str | None, user_id: int | None) -> dict:
    return {
        "id": event.id,
        "ref": f"E-{event.id}",
        "type": event.type,
        "subtype": event.subtype or "",
        "label": event.label,
        "title": event.title,
        "stage": event.stage,
        "sacco": event.sacco_name,
        "sacco_id": event.sacco_id,
        "fare": event.fare,
        "previous_fare": event.previous_fare,
        "note": event.note or "",
        "status": event.status,
        "confirmations": event.confirmations,
        "needed": event.needed,
        "cleared_votes": event.cleared_votes,
        "first_seen": _iso(event.first_seen),
        "last_seen": _iso(event.last_seen),
        "verified_at": _iso(event.verified_at),
        "expires_at": _iso(event.expires_at),
        "my_vote": my_vote,
        "i_reported": bool(user_id and event.reported_by_user_id == user_id),
    }


def _votes_for(
    db: Session, event_ids: list[int], user_id: int | None
) -> dict[int, str]:
    if not user_id or not event_ids:
        return {}
    rows = db.scalars(
        select(CommuterVote).where(
            CommuterVote.user_id == user_id, CommuterVote.event_id.in_(event_ids)
        )
    ).all()
    return {row.event_id: row.kind for row in rows}


def _subscribed_ids(db: Session, user: AppUser | None) -> set[int]:
    if user is None:
        return set()
    return set(
        db.scalars(
            select(RouteSubscription.route_id).where(RouteSubscription.user_id == user.id)
        ).all()
    )


def _active_surges(db: Session, now: datetime) -> dict[int, SurgeEvent]:
    rows = db.scalars(
        select(SurgeEvent)
        .where(SurgeEvent.is_active.is_(True), SurgeEvent.ends_at > now)
        .order_by(SurgeEvent.created_at.desc())
    ).all()
    result: dict[int, SurgeEvent] = {}
    for surge in rows:
        if surge.route_id is not None and surge.route_id not in result:
            result[surge.route_id] = surge
    return result


def _pill(events: list[CommuterEvent], surge: SurgeEvent | None) -> str:
    serious = {"jam", "route_closed", "accident_police"}
    if any(e.status == "verified" and e.type in serious for e in events):
        return "kwama"
    if surge is not None or any(e.status == "pending" for e in events):
        return "moderate"
    return "maji_safi"


def _route_list_item(
    group: list[Route],
    events: list[CommuterEvent],
    surge: SurgeEvent | None,
    subscribed: bool,
) -> dict:
    canonical = group[0]
    alerts = sum(1 for e in events if e.status == "verified")
    return {
        "id": canonical.id,
        "number": canonical.route_number,
        "name": f"{canonical.start_location} → {canonical.end_location}",
        "via": canonical.line.name,
        "destination": canonical.end_location,
        "pill": _pill(events, surge),
        "alert_count": alerts,
        "subscribed": subscribed,
    }


def _sacco_cards(
    group: list[Route],
    events: list[CommuterEvent],
    surges: dict[int, SurgeEvent],
) -> list[dict]:
    cards: list[dict] = []
    for row in group:
        usual = row.fare_min
        surge = surges.get(row.id)
        fare_events = [
            e
            for e in events
            if e.type == "fare_hike" and e.sacco_id == row.sacco_id
        ]
        event = fare_events[0] if fare_events else None

        if surge is not None and surge.multiplier > 1.0:
            fare = surge.adjusted_fare_min
            state = "up"
            delta = fare - usual
            reporters = event.confirmations if event else 0
            event_id = event.id if event else None
            updated = event.verified_at or event.last_seen if event else surge.updated_at
        elif event is not None and event.status == "verified":
            fare = event.fare or usual
            state = "up" if fare != usual else "normal"
            delta = fare - usual
            reporters = event.confirmations
            event_id = event.id
            updated = event.verified_at or event.last_seen
        elif event is not None:
            fare = event.fare or usual
            state = "pending"
            delta = fare - usual
            reporters = event.confirmations
            event_id = event.id
            updated = event.last_seen
        else:
            fare = usual
            state = "normal"
            delta = 0
            reporters = 0
            event_id = None
            updated = row.updated_at

        cards.append(
            {
                "id": row.sacco_id,
                "name": row.sacco.name,
                "usual_fare": usual,
                "fare": fare,
                "state": state,
                "delta": delta,
                "reporters": reporters,
                "event_id": event_id,
                "updated_at": _iso(updated),
            }
        )
    # De-duplicate saccos that appear more than once for the same route number.
    seen: set[int] = set()
    unique: list[dict] = []
    for card in cards:
        if card["id"] in seen:
            continue
        seen.add(card["id"])
        unique.append(card)
    return unique


def _stages(group: list[Route], events: list[CommuterEvent]) -> list[str]:
    canonical = group[0]
    stages: list[str] = []
    for name in (
        [canonical.start_location]
        + [e.stage for e in sorted(events, key=lambda e: e.first_seen or utcnow()) if e.stage]
        + [canonical.end_location]
    ):
        if name and name not in stages:
            stages.append(name)
    return stages


def _route_detail(
    db: Session,
    group: list[Route],
    user: AppUser | None,
    subscribed_ids: set[int],
    now: datetime,
) -> dict:
    canonical = group[0]
    events = _active_events(db, canonical.route_number, now)
    surges = _active_surges(db, now)
    votes = _votes_for(db, [e.id for e in events], user.id if user else None)
    serialized = [_event_dict(e, votes.get(e.id), user.id if user else None) for e in events]

    verified = [e for e in events if e.status == "verified"]
    banner = None
    if verified:
        serious = [
            e
            for e in verified
            if e.type in ("accident_police", "jam", "route_closed")
        ]
        top = max(serious or verified, key=lambda e: ensure_utc(e.verified_at or e.last_seen))
        banner = {
            "event_id": top.id,
            "title": top.title,
            "reports": top.confirmations,
            "verified_at": _iso(top.verified_at or top.last_seen),
            "event": _event_dict(top, votes.get(top.id), user.id if user else None),
        }

    latest = [ensure_utc(canonical.updated_at)]
    latest.extend(ensure_utc(e.last_seen) for e in events if e.last_seen)
    for surge in (surges.get(row.id) for row in group):
        if surge is not None:
            latest.append(ensure_utc(surge.updated_at))

    return {
        "id": canonical.id,
        "number": canonical.route_number,
        "name": f"{canonical.start_location} → {canonical.end_location}",
        "via": canonical.line.name,
        "destination": canonical.end_location,
        "pill": _pill(events, surges.get(canonical.id)),
        "alert_count": len(verified),
        "subscribed": canonical.id in subscribed_ids,
        "stages": _stages(group, events),
        "saccos": _sacco_cards(group, events, surges),
        "banner": banner,
        "events": serialized,
        "updated_at": _iso(max(latest)),
    }


def _stage_from_note(note: str | None, fallback: str | None) -> str | None:
    if note:
        haystack = note.lower()
        for name in sorted(load_locations(), key=len, reverse=True):
            if len(name) >= 4 and name.lower() in haystack:
                return name
    return fallback


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/routes", summary="List routes for the commuter app")
def list_routes(
    search: str = "",
    db: Session = Depends(get_db),
    user: AppUser | None = Depends(current_user_optional),
) -> list[dict]:
    now = utcnow()
    term = search.strip().lower()
    subscribed = _subscribed_ids(db, user)
    surges = _active_surges(db, now)
    events_by_route: dict[str, list[CommuterEvent]] = defaultdict(list)
    for event in _active_events(db, None, now):
        events_by_route[event.route_number].append(event)

    items: list[dict] = []
    for group in _route_groups(db):
        canonical = group[0]
        if term:
            haystack = " ".join(
                [
                    canonical.route_number,
                    canonical.start_location,
                    canonical.end_location,
                    canonical.line.name,
                    canonical.sacco.name,
                ]
            ).lower()
            if term not in haystack:
                continue
        events = events_by_route.get(canonical.route_number, [])
        surge = next((surges.get(row.id) for row in group if surges.get(row.id)), None)
        items.append(
            _route_list_item(group, events, surge, canonical.id in subscribed)
        )
    return items


@router.get("/routes/{route_id}", summary="Route detail for the commuter app")
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    user: AppUser | None = Depends(current_user_optional),
) -> dict:
    group = _group_for_id(db, route_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return _route_detail(db, group, user, _subscribed_ids(db, user), utcnow())


@router.post("/routes/{route_id}/subscribe", summary="Toggle route alerts")
def toggle_subscribe(
    route_id: int,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_user),
) -> dict:
    group = _group_for_id(db, route_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Route not found")
    canonical_id = group[0].id
    existing = db.scalar(
        select(RouteSubscription).where(
            RouteSubscription.user_id == user.id,
            RouteSubscription.route_id == canonical_id,
        )
    )
    if existing is not None:
        db.delete(existing)
        subscribed = False
    else:
        db.add(RouteSubscription(user_id=user.id, route_id=canonical_id))
        subscribed = True
    db.commit()
    return {"subscribed": subscribed}


# ── Reports and votes ────────────────────────────────────────────────────────


class ReportIn(BaseModel):
    route: int
    type: str
    subtype: str | None = None
    sacco: int | None = None
    fare: int | None = Field(default=None, ge=10, le=999)
    note: str | None = Field(default=None, max_length=280)


class VoteIn(BaseModel):
    kind: str


REPORT_TYPES = {"fare_hike", "jam", "accident_police", "route_closed"}


@router.post("/reports", status_code=201, summary="Submit a commuter report")
def create_report(
    payload: ReportIn,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_user),
) -> dict:
    if payload.type not in REPORT_TYPES:
        raise HTTPException(status_code=422, detail="Unknown report type.")
    if payload.type == "fare_hike" and payload.fare is None:
        raise HTTPException(status_code=422, detail="A fare hike needs a fare.")

    group = _group_for_id(db, payload.route)
    if group is None:
        raise HTTPException(status_code=404, detail="Route not found")
    canonical = group[0]
    now = utcnow()

    sacco_row = canonical
    if payload.sacco is not None:
        sacco_row = next(
            (row for row in group if row.sacco_id == payload.sacco), canonical
        )
    sacco = db.get(Sacco, sacco_row.sacco_id) if sacco_row.sacco_id else None

    stage = _stage_from_note(
        payload.note,
        canonical.end_location if payload.type != "fare_hike" else canonical.start_location,
    )
    subtype = (payload.subtype or "") if payload.type == "accident_police" else ""
    label = _event_label(payload.type, subtype)

    previous_fare = sacco_row.fare_min
    if payload.type == "fare_hike":
        recent_fare = db.scalar(
            select(CommuterEvent)
            .where(
                CommuterEvent.route_number == canonical.route_number,
                CommuterEvent.type == "fare_hike",
                CommuterEvent.sacco_id == sacco_row.sacco_id,
                CommuterEvent.status == "verified",
            )
            .order_by(CommuterEvent.verified_at.desc())
        )
        if recent_fare is not None and recent_fare.fare:
            previous_fare = recent_fare.fare

    if payload.type == "fare_hike":
        title = f"Fare hike: {sacco.name if sacco else canonical.route_number} KES {previous_fare} → {payload.fare}"
    elif payload.type == "jam":
        title = f"Jam at {stage}"
    elif payload.type == "route_closed":
        title = f"Route closed at {stage}"
    else:
        title = f"{label} at {stage}"

    # Merge with a recent, still-open report of the same kind.
    existing = db.scalar(
        select(CommuterEvent)
        .where(
            CommuterEvent.route_number == canonical.route_number,
            CommuterEvent.type == payload.type,
            CommuterEvent.subtype == subtype,
            CommuterEvent.sacco_id == (sacco_row.sacco_id if payload.type == "fare_hike" else None),
            CommuterEvent.status.in_(("pending", "verified")),
            CommuterEvent.last_seen >= now - 2 * HOUR,
        )
        .order_by(CommuterEvent.last_seen.desc())
    )

    verified_now = False
    merged_count = 0
    if existing is not None:
        merged_count = existing.confirmations
        existing.confirmations += 1
        existing.last_seen = now
        existing.note = payload.note or existing.note
        existing.stage = stage or existing.stage
        if payload.type == "fare_hike" and payload.fare:
            existing.previous_fare = previous_fare
            existing.fare = payload.fare
            existing.title = title
        if existing.status == "pending" and existing.confirmations >= VERIFY_AT:
            existing.status = "verified"
            existing.verified_at = now
            verified_now = True
        existing.needed = max(0, VERIFY_AT - existing.confirmations)
        event = existing
    else:
        lifetime = 6 * HOUR if payload.type == "fare_hike" else HOUR
        event = CommuterEvent(
            route_id=canonical.id,
            route_number=canonical.route_number,
            type=payload.type,
            subtype=subtype,
            label=label,
            title=title,
            stage=stage,
            sacco_id=sacco_row.sacco_id if payload.type == "fare_hike" else None,
            sacco_name=sacco.name if (sacco and payload.type == "fare_hike") else None,
            fare=payload.fare if payload.type == "fare_hike" else None,
            previous_fare=previous_fare if payload.type == "fare_hike" else None,
            note=payload.note or "",
            status="pending",
            confirmations=1,
            needed=VERIFY_AT - 1,
            cleared_votes=0,
            source="app",
            phone=user.phone,
            reported_by_user_id=user.id,
            first_seen=now,
            last_seen=now,
            expires_at=now + lifetime,
        )
        db.add(event)

    db.commit()
    db.refresh(event)

    others_count = max(0, event.confirmations - 1)
    return {
        "event": _event_dict(event, "still", user.id),
        "others_count": others_count,
        "merged_count": merged_count,
        "verified_now": verified_now,
    }


@router.post("/events/{event_id}/vote", summary="Confirm or clear an event")
def vote(
    event_id: int,
    payload: VoteIn,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_user),
) -> dict:
    if payload.kind not in ("still", "cleared"):
        raise HTTPException(status_code=422, detail="Vote must be 'still' or 'cleared'.")
    event = db.get(CommuterEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    now = utcnow()
    record = db.scalar(
        select(CommuterVote).where(
            CommuterVote.event_id == event.id, CommuterVote.user_id == user.id
        )
    )
    previous = record.kind if record is not None else None

    if payload.kind == "still":
        if previous != "still":
            event.confirmations += 1
        if event.status == "pending" and event.confirmations >= VERIFY_AT:
            event.status = "verified"
            event.verified_at = now
    else:
        if previous == "still":
            event.confirmations = max(0, event.confirmations - 1)
        if previous != "cleared":
            event.cleared_votes += 1
        if event.cleared_votes >= VERIFY_AT:
            event.status = "cleared"

    event.needed = max(0, VERIFY_AT - event.confirmations)
    event.last_seen = now

    if record is None:
        db.add(CommuterVote(event_id=event.id, user_id=user.id, kind=payload.kind))
    else:
        record.kind = payload.kind
    db.commit()
    db.refresh(event)

    return _event_dict(event, payload.kind, user.id)


# ── Signal panel ─────────────────────────────────────────────────────────────

SPAM_SAMPLES = [
    ("win iphone 15, click hapa", "07•• ••• 777", "blocklist"),
    ("asante", "07•• ••• 565", "unparseable"),
    ("test", "07•• ••• 186", "unparseable"),
    ("ok", "07•• ••• 074", "unparseable"),
    ("?", "07•• ••• 203", "unparseable"),
]


def _signal(db: Session) -> dict:
    now = utcnow()
    events = list(
        db.scalars(
            select(CommuterEvent).order_by(CommuterEvent.last_seen.desc())
        ).all()
    )
    pending = [e for e in events if e.status == "pending"]
    verified = [e for e in events if e.status in ("verified", "cleared")]

    reports: list[dict] = []
    for index, (text, phone, reason) in enumerate(SPAM_SAMPLES):
        reports.append(
            {
                "id": 9000 + index,
                "text": text,
                "source": "sms",
                "phone": phone,
                "at": _iso(now - timedelta(minutes=3 + index * 2)),
                "is_spam": True,
                "spam_reason": reason,
                "event_ref": None,
                "event_label": None,
            }
        )
    for event in events:
        reports.append(
            {
                "id": event.id,
                "text": event.note or event.title,
                "source": "app" if event.source == "app" else "sms",
                "phone": mask_phone(event.phone) if event.phone else "07•• ••• 000",
                "at": _iso(event.last_seen),
                "is_spam": False,
                "spam_reason": "",
                "event_ref": f"E-{event.id}",
                "event_label": event.label.split()[0],
            }
        )
    reports.sort(key=lambda item: item["at"] or "", reverse=True)

    verified_events = [
        {
            "id": e.id,
            "ref": f"E-{e.id}",
            "title": e.title,
            "routes": f"Route {e.route_number}",
            "stage": e.stage,
            "type": e.type,
            "status": e.status,
            "reports": e.confirmations,
            "first_seen": _iso(e.first_seen),
            "verified_at": _iso(e.verified_at),
        }
        for e in sorted(
            events,
            key=lambda e: ensure_utc(e.verified_at or e.last_seen),
            reverse=True,
        )
        if e.status in ("verified", "cleared", "expired")
    ]

    notifications = db.scalars(
        select(Notification).order_by(Notification.created_at.desc()).limit(15)
    ).all()
    alerts = []
    for note in notifications:
        route_match = re.search(r"(?:Route|update:\s*)([0-9][0-9A-Za-z/]*)", note.title)
        alerts.append(
            {
                "id": note.id,
                "sent_at": _iso(note.sent_at or note.created_at),
                "text": note.title,
                "routes": route_match.group(1) if route_match else "—",
                "sent_to": "subscribers · push",
                "recipients": 0,
                "status": "Active" if note.notification_type in ("surge", "accident") else "Cleared",
            }
        )

    spam_count = len(SPAM_SAMPLES)
    return {
        "funnel": {
            "raw": len(events) + spam_count,
            "spam": spam_count,
            "events": len(events),
            "verified": len(verified),
        },
        "pending_count": len(pending),
        "reports": reports[:40],
        "verified_events": verified_events,
        "alerts": alerts,
    }


@router.get("/signal", summary="Signal panel data")
def signal(
    db: Session = Depends(get_db),
    _: AppUser | None = Depends(current_user_optional),
) -> dict:
    return _signal(db)


@router.post("/demo/replay", summary="Replay the demo feed (staff only)")
def replay_demo(user: AppUser = Depends(require_user)) -> dict:
    # The demo seed is idempotent and no SMS is sent. Only expose the action to
    # staff accounts; ordinary commuters simply get a no-op.
    if not getattr(user, "is_staff", False):
        return {"replayed": 0, "message": "Demo replay is available to staff only."}
    return {"replayed": 0, "message": "Demo feed is already up to date."}


# ── Seeding ──────────────────────────────────────────────────────────────────


def seed_demo_events(db: Session) -> int:
    """Seed a handful of realistic reports for route 100 once.

    Called at startup only when tables were just created. No notifications or
    SMS are sent; these rows are plain database records.
    """
    if db.scalar(select(CommuterEvent.id).limit(1)) is not None:
        return 0
    route = db.scalar(select(Route).where(Route.route_number == "100").order_by(Route.id))
    if route is None:
        return 0
    sacco = db.get(Sacco, route.sacco_id)
    now = utcnow()

    demo = [
        {
            "type": "accident_police",
            "subtype": "accident",
            "title": "Accident at Ngara",
            "stage": "Ngara",
            "note": "ajali ngara, matatu imegongwa",
            "status": "verified",
            "confirmations": 5,
            "verified_minutes": 18,
            "lifetime_hours": 2,
            "sacco_id": None,
            "sacco_name": None,
        },
        {
            "type": "fare_hike",
            "subtype": "",
            "title": f"Fare hike: {sacco.name if sacco else 'Super Metro'} KES 80 → 100",
            "stage": "Roysambu",
            "note": "100 bob odeon to g45 ni wizi",
            "status": "verified",
            "confirmations": 6,
            "verified_minutes": 25,
            "lifetime_hours": 6,
            "sacco_id": route.sacco_id,
            "sacco_name": sacco.name if sacco else None,
            "fare": 100,
            "previous_fare": 80,
        },
        {
            "type": "jam",
            "subtype": "",
            "title": "Jam at Kasarani",
            "stage": "Kasarani",
            "note": "imejam kasarani bana, hatusongi",
            "status": "verified",
            "confirmations": 4,
            "verified_minutes": 10,
            "lifetime_hours": 1,
            "sacco_id": None,
            "sacco_name": None,
        },
        {
            "type": "accident_police",
            "subtype": "police",
            "title": "Police check at Githurai 45",
            "stage": "Githurai",
            "note": "karao wako stage githurai 45",
            "status": "pending",
            "confirmations": 2,
            "verified_minutes": None,
            "lifetime_hours": 1,
            "sacco_id": None,
            "sacco_name": None,
        },
    ]

    for item in demo:
        verified_at = (
            now - timedelta(minutes=item["verified_minutes"])
            if item["verified_minutes"] is not None
            else None
        )
        event = CommuterEvent(
            route_id=route.id,
            route_number=route.route_number,
            type=item["type"],
            subtype=item["subtype"],
            label=_event_label(item["type"], item["subtype"]),
            title=item["title"],
            stage=item["stage"],
            sacco_id=item.get("sacco_id"),
            sacco_name=item.get("sacco_name"),
            fare=item.get("fare"),
            previous_fare=item.get("previous_fare"),
            note=item["note"],
            status=item["status"],
            confirmations=item["confirmations"],
            needed=max(0, VERIFY_AT - item["confirmations"]),
            cleared_votes=0,
            source="sms",
            phone="+254700000000",
            first_seen=verified_at or (now - timedelta(minutes=20)),
            last_seen=now - timedelta(minutes=2),
            verified_at=verified_at,
            expires_at=now + timedelta(hours=item["lifetime_hours"]),
        )
        db.add(event)

    db.commit()
    logger.info("seeded %s demo community events for route %s", len(demo), route.route_number)
    return len(demo)
