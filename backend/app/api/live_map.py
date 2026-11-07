from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

router = APIRouter(tags=["map"])


@router.get("/map", include_in_schema=False)
def live_map() -> FileResponse:
    """Serve the OpenStreetMap + Leaflet route and incident map."""
    return FileResponse(STATIC_DIR / "live-map.html", media_type="text/html")
