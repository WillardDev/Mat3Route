"""One-time geocoder for Mat3 route place names.

Reads data/scraped_routes.csv, resolves each unique start/end location through
OpenStreetMap Nominatim, and writes backend/app/data/nairobi_locations.json.

Nominatim usage policy: one request per second, valid User-Agent, results cached.
Run with:  .venv/bin/python scripts/geocode_locations.py
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "scraped_routes.csv"
OUT_PATH = ROOT / "backend" / "app" / "data" / "nairobi_locations.json"
USER_AGENT = "Mat3Route-dev/0.1 (local development; contact: dev@mat3route.local)"
URL = "https://nominatim.openstreetmap.org/search"

# Ambiguous stage names that Nominatim resolves poorly.
MANUAL: dict[str, tuple[float, float]] = {
    "Roundabout": (-1.2923, 36.8410),
    "GM": (-1.2863, 36.8415),
    "KPA": (-1.3300, 36.8480),
    "Hardy": (-1.3231, 36.7080),
    "Caltex": (-1.2997, 36.8873),
    "Highrise": (-1.3090, 36.8170),
    "Joster": (-1.2950, 36.9000),
    "Rikana": (-1.2971, 36.8942),
    "Gasolina": (-1.1600, 36.7000),
    "Kaberia": (-1.2500, 36.7200),
    "Ayani": (-1.3054, 36.7759),
    "Nakumatt": (-1.2670, 36.7500),
    "Kenyatta": (-1.3008, 36.8072),
    "Lunga Lunga": (-1.3095, 36.8570),
    "Baba Ndogo": (-1.2439, 36.8813),
    "Komarock Roundabout": (-1.2720, 36.9050),
    "Pipeline Jogoo": (-1.3120, 36.8850),
    "Umoja": (-1.2834, 36.8928),
    "Umoja/Donholm": (-1.2992, 36.8887),
    # Nominatim returns county/city-district centroids for these names; use the
    # actual town, suburb, or road instead.
    "Kiambu": (-1.1663925, 36.8252791),
    "Kikuyu": (-1.2438129, 36.6646904),
    "Langata": (-1.3328938, 36.7816659),
    "Othaya": (-1.2853440, 36.7749715),
}


def unique_locations() -> list[str]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    names = sorted(
        {row["start"].strip() for row in rows}
        | {row["end"].strip() for row in rows}
    )
    return [name for name in names if name]


def geocode(client: httpx.Client, name: str) -> dict | None:
    response = client.get(
        URL,
        params={
            "q": f"{name}, Kenya",
            "format": "jsonv2",
            "limit": 5,
            "countrycodes": "ke",
            "addressdetails": 1,
            # Bias towards Nairobi without excluding nearby towns.
            "viewbox": "36.35,-1.70,37.35,-0.80",
            "bounded": 0,
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return results[0]


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    places: dict[str, dict] = {}

    with httpx.Client() as client:
        for index, name in enumerate(unique_locations(), start=1):
            if name in MANUAL:
                lat, lon = MANUAL[name]
                places[name] = {
                    "lat": lat,
                    "lon": lon,
                    "display_name": f"{name}, Kenya (manual)",
                    "source": "manual",
                }
                print(f"[{index:2}] {name} -> manual {lat:.5f},{lon:.5f}")
                continue

            try:
                result = geocode(client, name)
            except httpx.HTTPError as exc:
                print(f"[{index:2}] {name} -> ERROR {exc}")
                continue

            if result is None:
                print(f"[{index:2}] {name} -> no result")
                continue

            places[name] = {
                "lat": float(result["lat"]),
                "lon": float(result["lon"]),
                "display_name": result.get("display_name"),
                "source": "nominatim",
            }
            print(
                f"[{index:2}] {name} -> {places[name]['lat']:.5f},"
                f"{places[name]['lon']:.5f}  {result.get('display_name', '')[:70]}"
            )
            time.sleep(1.1)

    OUT_PATH.write_text(json.dumps(places, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(places)} locations to {OUT_PATH}")


if __name__ == "__main__":
    main()
