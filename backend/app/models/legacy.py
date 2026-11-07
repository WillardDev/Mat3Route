from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from ..utils import utcnow


class RouteLine(Base):
    __tablename__ = "route_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    routes: Mapped[list[Route]] = relationship(back_populates="line")


class Sacco(Base):
    __tablename__ = "saccos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    routes: Mapped[list[Route]] = relationship(back_populates="sacco")


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint(
            "line_id",
            "route_number",
            "start_location",
            "end_location",
            "sacco_id",
            name="routes_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("route_lines.id"), nullable=False)
    route_number: Mapped[str] = mapped_column(Text, nullable=False)
    start_location: Mapped[str] = mapped_column(Text, nullable=False)
    end_location: Mapped[str] = mapped_column(Text, nullable=False)
    sacco_id: Mapped[int] = mapped_column(ForeignKey("saccos.id"), nullable=False)
    fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
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

    line: Mapped[RouteLine] = relationship(back_populates="routes")
    sacco: Mapped[Sacco] = relationship(back_populates="routes")
    users: Mapped[list[AppUser]] = relationship(back_populates="route")


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text, default="Nairobi", server_default="Nairobi", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    route: Mapped[Route | None] = relationship(back_populates="users")
    devices: Mapped[list[NotificationDevice]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")


class NotificationDevice(Base):
    __tablename__ = "notification_devices"
    __table_args__ = (UniqueConstraint("provider", "token", name="notification_devices_provider_token_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, default="thrivewave", nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped[AppUser] = relationship(back_populates="devices")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    __table_args__ = (Index("weather_snapshots_city_fetched_idx", "city", "fetched_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    condition_code: Mapped[int | None] = mapped_column(Integer)
    condition_main: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    feels_like_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[int | None] = mapped_column(Integer)
    wind_speed_mps: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AccidentReport(Base):
    __tablename__ = "accident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_users.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, default="medium", nullable=False)
    status: Mapped[str] = mapped_column(Text, default="reported", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high')", name="accident_reports_severity_check"),
        CheckConstraint(
            "status IN ('reported', 'verified', 'resolved', 'rejected')",
            name="accident_reports_status_check",
        ),
    )

    route: Mapped[Route] = relationship()
    reported_by: Mapped[AppUser | None] = relationship()


class SurgeEvent(Base):
    __tablename__ = "surge_events"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('weather', 'accident', 'peak_hour', 'combined', 'manual')",
            name="surge_events_trigger_type_check",
        ),
        CheckConstraint("multiplier >= 1.0", name="surge_events_multiplier_check"),
        Index("surge_events_route_active_idx", "route_id", "is_active"),
        Index(
            "surge_events_one_active_per_route",
            "route_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    weather_component: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    accident_component: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    peak_component: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    base_fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    base_fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    weather_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("weather_snapshots.id", ondelete="SET NULL")
    )
    accident_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("accident_reports.id", ondelete="SET NULL")
    )
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

    route: Mapped[Route | None] = relationship()
    weather_snapshot: Mapped[WeatherSnapshot | None] = relationship()
    accident_report: Mapped[AccidentReport | None] = relationship()


class FareQuote(Base):
    __tablename__ = "fare_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    surge_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("surge_events.id", ondelete="SET NULL")
    )
    multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    base_fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    base_fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    route: Mapped[Route] = relationship()
    user: Mapped[AppUser | None] = relationship()
    surge_event: Mapped[SurgeEvent | None] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(Text, nullable=False)
    weather_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("weather_snapshots.id", ondelete="SET NULL")
    )
    surge_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("surge_events.id", ondelete="SET NULL")
    )
    accident_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("accident_reports.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(Text, unique=True)
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('weather', 'surge', 'accident', 'system')",
            name="notifications_type_check",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'skipped')",
            name="notifications_status_check",
        ),
    )

    user: Mapped[AppUser] = relationship(back_populates="notifications")
