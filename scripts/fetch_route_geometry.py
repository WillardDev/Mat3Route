"""One-time road geometry fetcher for Mat3 route stage pairs.

Reads data/scraped_routes.csv plus the cached stage coordinates, asks the public
OSRM demo server for a driving route between each unique start/end pair,
simplifies the result, and writes backend/app/data/route_geometry.json.

The cache is keyed by ``"start|end"``. Existing entries are kept, so the script
can be re-run to fill gaps after a failure. Use ``--force`` to refetch all.

OSRM's public demo server is for development and one-off caching only. For
production, self-host OSRM or use a commercial routing provider.

Run with:  .venv/bin/python scripts/fetch_route_geometry.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "scraped_routes.csv"
LOCATIONS_PATH = ROOT / "backend" / "app" / "data" / "nairobi_locations.json"
OUT_PATH = ROOT / "backend" / "app" / "data" / "route_geometry.json"

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{coordinates}"
USER_AGENT = "Mat3Route-dev/0.1 (local development; contact: dev@mat3route.local)"
TOLERANCE = 0.0001  # ~11 m in degrees; keeps road shape without huge payloads.
SLEEP_SECONDS = 1.0


def unique_pairs() -> list[tuple[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    pairs = {(row["start"].strip(), row["end"].strip()) for row in rows}
    return sorted(pair for pair in pairs if pair[0] and pair[1])


def load_locations() -> dict[str, tuple[float, float]]:
    data = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    return {
        name: (float(value["lat"]), float(value["lon"]))
        for name, value in data.items()
    }


def perpendicular_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    """Distance from point to the start-end segment in degrees."""
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(
    points: list[tuple[float, float]], tolerance: float
) -> list[tuple[float, float]]:
    """Douglas-Peucker simplification for [lon, lat] points."""
    if len(points) < 3:
        return points

    furthest, split_index = 0.0, 0
    for index in range(1, len(points) - 1):
        distance = perpendicular_distance(points[index], points[0], points[-1])
        if distance > furthest:
            furthest, split_index = distance, index

    if furthest > tolerance:
        left = simplify(points[: split_index + 1], tolerance)
        right = simplify(points[split_index:], tolerance)
        return left[:-1] + right
    return [points[0], points[-1]]


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance between two (lat, lon) points in metres."""
    radius = 6_371_000
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def fetch_route(
    client: httpx.Client,
    start: tuple[float, float],
    end: tuple[float, float],
) -> dict:
    coordinates = f"{start[1]:.6f},{start[0]:.6f};{end[1]:.6f},{end[0]:.6f}"
    response = client.get(
        OSRM_URL.format(coordinates=coordinates),
        params={
            "overview": "full",
            "geometries": "geojson",
            "alternatives": "false",
            "steps": "false",
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM returned {data.get('code')}")

    route = data["routes"][0]
    geometry = route["geometry"]["coordinates"]
    simplified = simplify([(lon, lat) for lon, lat in geometry], TOLERANCE)
    path = [[round(lat, 5), round(lon, 5)] for lon, lat in simplified]
    if len(path) < 2:
        raise RuntimeError("OSRM returned fewer than two points")

    snapped_start = (path[0][0], path[0][1])
    snapped_end = (path[-1][0], path[-1][1])
    start_offset = haversine_m(start, snapped_start)
    end_offset = haversine_m(end, snapped_end)
    if start_offset > 2_000:
        print(f"    warning: start snapped {start_offset / 1000:.1f} km away")
    if end_offset > 2_000:
        print(f"    warning: end snapped {end_offset / 1000:.1f} km away")

    return {
        "distance_km": round(route["distance"] / 1000, 1),
        "duration_min": round(route["duration"] / 60, 1),
        "path": path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="refetch cached pairs")
    args = parser.parse_args()

    locations = load_locations()
    pairs = unique_pairs()

    if OUT_PATH.exists() and not args.force:
        geometry = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    else:
        geometry = {}

    missing_locations = sorted(
        {name for pair in pairs for name in pair if name not in locations}
    )
    if missing_locations:
        raise SystemExit(f"missing coordinates for: {missing_locations}")

    pending = [pair for pair in pairs if args.force or f"{pair[0]}|{pair[1]}" not in geometry]
    print(f"{len(pairs)} unique stage pairs, {len(pending)} to fetch")

    failures: list[tuple[str, str, str]] = []
    with httpx.Client() as client:
        for index, (start_name, end_name) in enumerate(pending, start=1):
            key = f"{start_name}|{end_name}"
            start = locations[start_name]
            end = locations[end_name]
            print(f"[{index:2}/{len(pending)}] {start_name} -> {end_name}", end=" ")

            last_error = ""
            for attempt in range(1, 4):
                try:
                    geometry[key] = fetch_route(client, start, end)
                    path = geometry[key]["path"]
                    print(
                        f"ok · {geometry[key]['distance_km']} km · "
                        f"{geometry[key]['duration_min']} min · {len(path)} pts"
                    )
                    break
                except (httpx.HTTPError, RuntimeError, KeyError) as exc:
                    last_error = str(exc)
                    if attempt < 3:
                        time.sleep(attempt * 2)
            else:
                print(f"FAILED · {last_error}")
                failures.append((start_name, end_name, last_error))

            OUT_PATH.write_text(
                json.dumps(dict(sorted(geometry.items())), separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            time.sleep(SLEEP_SECONDS)

    total_points = sum(len(value["path"]) for value in geometry.values())
    print(f"\nWrote {len(geometry)} paths ({total_points} points) to {OUT_PATH}")
    if failures:
        print(f"{len(failures)} failed pairs; re-run to retry them:")
        for start_name, end_name, error in failures:
            print(f"  {start_name} -> {end_name}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
