from __future__ import annotations

from ..models import Route


def serialize_route(route: Route) -> dict:
    return {
        "id": route.id,
        "line": route.line.name,
        "route_number": route.route_number,
        "start": route.start_location,
        "end": route.end_location,
        "sacco": route.sacco.name,
        "sacco_code": route.sacco.code,
        "base_fare_min": route.fare_min,
        "base_fare_max": route.fare_max,
    }
