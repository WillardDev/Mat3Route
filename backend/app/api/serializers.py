from __future__ import annotations

from ..locations import coordinates_for
from ..models import Route
from ..route_geometry import geometry_for


def serialize_route(route: Route) -> dict:
    start = coordinates_for(route.start_location)
    end = coordinates_for(route.end_location)
    path = geometry_for(route.start_location, route.end_location)
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
        "start_lat": start[0] if start else None,
        "start_lon": start[1] if start else None,
        "end_lat": end[0] if end else None,
        "end_lon": end[1] if end else None,
        "path": [[latitude, longitude] for latitude, longitude in path] if path else None,
    }
