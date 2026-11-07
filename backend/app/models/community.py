"""Community reporting models used by the MatatuPulse frontend.

These tables back the commuter-facing API (``/api/routes``, ``/api/reports``,
``/api/events/{id}/vote``). They deliberately live beside the older
``legacy`` models so the existing sync stack can keep using the same ``Base``.

Note: the columns reference ``app_users``/``routes``/``saccos`` by integer id
without database-level foreign keys. The application role can create tables but
is not the owner of the existing schema, so FK constraints would need extra
grants on a local database.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils import utcnow


class RouteSubscription(Base):
    __tablename__ = "route_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "route_id", name="route_subscriptions_user_route_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )


class CommuterEvent(Base):
    """A single commuter report / verified event for one route."""

    __tablename__ = "commuter_events"
    __table_args__ = (
        Index("commuter_events_route_status_idx", "route_number", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    route_number: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    subtype: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str | None] = mapped_column(Text)
    sacco_id: Mapped[int | None] = mapped_column(Integer)
    sacco_name: Mapped[str | None] = mapped_column(Text)
    fare: Mapped[int | None] = mapped_column(Integer)
    previous_fare: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending", nullable=False)
    confirmations: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    needed: Mapped[int] = mapped_column(Integer, default=2, server_default="2", nullable=False)
    cleared_votes: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    source: Mapped[str] = mapped_column(Text, default="app", server_default="app", nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    reported_by_user_id: Mapped[int | None] = mapped_column(Integer)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class CommuterVote(Base):
    __tablename__ = "commuter_votes"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="commuter_votes_event_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )


__all__ = ["CommuterEvent", "CommuterVote", "RouteSubscription"]
