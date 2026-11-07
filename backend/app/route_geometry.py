from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

GEOMETRY_PATH = Path(__file__).resolve().parent / "data" / "route_geometry.json"

Point = tuple[float, float]


@lru_cache(maxsize=1)
def load_route_geometry() -> dict[str, tuple[Point, ...]]:
    """Load cached OSRM road paths keyed by ``"start|end"``."""
    data = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    return {
        key: tuple((float(point[0]), float(point[1])) for point in value["path"])
        for key, value in data.items()
    }


def geometry_for(start: str | None, end: str | None) -> tuple[Point, ...] | None:
    if not start or not end:
        return None
    return load_route_geometry().get(f"{start.strip()}|{end.strip()}")
