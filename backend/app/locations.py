from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCATIONS_PATH = Path(__file__).resolve().parent / "data" / "nairobi_locations.json"


@lru_cache(maxsize=1)
def load_locations() -> dict[str, tuple[float, float]]:
    """Load the cached OpenStreetMap coordinates for route place names."""
    data = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    return {
        name: (float(value["lat"]), float(value["lon"]))
        for name, value in data.items()
    }


def coordinates_for(name: str | None) -> tuple[float, float] | None:
    if not name:
        return None
    return load_locations().get(name.strip())
