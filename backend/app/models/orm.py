"""SQLAlchemy ORM models mirroring the Mat3Route schema."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP

from ..database import Base


class RouteLine(Base):
    __tablename__ = "route_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    routes: Mapped[list["Route"]] = relationship("Route", back_populates="line")


class Sacco(Base):
    __tablename__ = "saccos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    routes: Mapped[list["Route"]] = relationship("Route", back_populates="sacco")


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint(
            "line_id", "route_number", "start_location", "end_location", "sacco_id",
            name="routes_unique",
        ),
        CheckConstraint("fare_min >= 0", name="routes_fare_min_check"),
        CheckConstraint("fare_max >= fare_min", name="routes_fare_max_check"),
        Index("routes_route_number_idx", "route_number"),
        Index("routes_start_location_idx", "start_location"),
        Index("routes_end_location_idx", "end_location"),
        Index("routes_sacco_idx", "sacco_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_id: Mapped[int] = mapped_column(Integer, ForeignKey("route_lines.id"), nullable=False)
    route_number: Mapped[str] = mapped_column(Text, nullable=False)
    start_location: Mapped[str] = mapped_column(Text, nullable=False)
    end_location: Mapped[str] = mapped_column(Text, nullable=False)
    sacco_id: Mapped[int] = mapped_column(Integer, ForeignKey("saccos.id"), nullable=False)
    fare_min: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_max: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    line: Mapped["RouteLine"] = relationship("RouteLine", back_populates="routes")
    sacco: Mapped["Sacco"] = relationship("Sacco", back_populates="routes")
