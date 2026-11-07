# Mat3Route — Weather Alerts & Dynamic Fare Surge System

This repository contains the Mat3 route database plus a FastAPI backend that:

- Polls OpenWeatherMap and detects significant weather changes.
- Calculates dynamic fare surcharges from weather, user-reported accidents, and rush-hour windows.
- Sends notifications through a provider-agnostic adapter (ThriveWave adapter included, mock provider for local development).
- Persists fare quotes, surge events, weather history, accident reports, and notification delivery status.

## Project layout

```
data/scraped_routes.csv      Raw route data
db/schema.sql                Core route tables
db/surge_system.sql          Weather, surge, accident, quote, and notification tables
scripts/setup_routes_db.sh   Creates DB, applies schema, imports routes
scripts/geocode_locations.py One-time OpenStreetMap geocoder for stage names
scripts/fetch_route_geometry.py One-time OSRM road-path fetcher for route pairs
backend/                     FastAPI application
  app/
    api/                     HTTP routers
    data/                    Cached stage coordinates and road paths
    providers/               Mock + ThriveWave notification adapters
    services/                Weather, surge engine, notifications, automation
    static/live-map.html     OpenStreetMap + Leaflet live map
    config.py                Environment settings
    models.py                SQLAlchemy models
    scheduler.py             APScheduler jobs
  tests/                     Pytest suite
docs/architecture.md         Design details and extension notes
```

## Quick start

### 1. Database

```bash
./scripts/setup_routes_db.sh
```

This creates `mat3route_dev`, applies all schemas, and imports the 97 routes.

### 2. Environment

```bash
cp .env.example .env
```

Set at minimum:

```env
DATABASE_URL=postgresql://mat3route:your_password@localhost:5432/mat3route_dev
OPENWEATHER_API_KEY=your_openweather_api_key
NOTIFICATION_PROVIDER=mock
ADMIN_API_TOKEN=change_me
```

The local `.env` is git-ignored. `.env.example` is the committed template.

### 3. Install and run

```bash
python3 -m venv .venv
.venv/bin/pip install -e "backend[dev]"
cd backend
../.venv/bin/python -m app.seed
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

The scheduler starts with the app and runs weather polling, surge refresh, and
surge expiry jobs. Set `SCHEDULER_ENABLED=false` to disable it.

### 4. Test

```bash
cd backend
../.venv/bin/pytest
```

## Live map

Start the API and open:

```
http://localhost:8000/map
```

The page uses Leaflet with OpenStreetMap raster tiles and shows:

- All 97 routes, coloured by line, with search and line filters.
- Incident markers coloured by severity and faded when resolved/rejected.
- Click-through from either list to the map, with route and incident popups.
- Live fare lookup when a route is selected.
- Browser geolocation ("Near me"), fit-to-routes, manual refresh, and a
  30-second auto-refresh.

Routes are drawn along roads using cached OSRM driving paths between stage
coordinates. The paths are **fastest driving routes**, so they may differ from
the exact corridor a sacco uses, but they no longer cut across buildings and
parks. Geometry is cached in `backend/app/data/route_geometry.json`, keyed by
`"start|end"`, so the map does not call a routing service at runtime.

Two one-time data scripts keep the map working offline:

```bash
.venv/bin/python scripts/geocode_locations.py      # stage coordinates
.venv/bin/python scripts/fetch_route_geometry.py   # road paths (resumable)
```

The geocoder uses OpenStreetMap Nominatim and the paths use the public OSRM demo
server. Both are suitable for development and one-off caching only. For
production, use a commercial routing provider or self-host OSRM/Nominatim.

OSM's public tile server is also suitable for development. Use a production tile
provider or self-hosted tiles for app traffic, and keep the OSM attribution.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service, DB, provider, and weather configuration status |
| `GET` | `/map` | Live OpenStreetMap route and incident map |
| `POST` | `/api/v1/users` | Create an app user |
| `POST` | `/api/v1/users/{id}/devices` | Register a push device/subscriber token |
| `GET` | `/api/v1/routes` | List/filter routes |
| `GET` | `/api/v1/routes/{id}/fare` | Current fare including any active surge |
| `POST` | `/api/v1/quotes` | Create a time-limited fare quote |
| `GET` | `/api/v1/weather/current` | Latest stored weather snapshot |
| `POST` | `/api/v1/weather/refresh` | Force an OpenWeatherMap poll (admin) |
| `POST` | `/api/v1/accidents` | Report a route disruption |
| `PATCH` | `/api/v1/accidents/{id}/status` | Verify/resolve/reject a report (admin) |
| `GET` | `/api/v1/surges` | List active surge events |
| `POST` | `/api/v1/surges/recalculate` | Recalculate all routes (admin) |
| `POST` | `/api/v1/surges/expire` | Expire stale surge events (admin) |
| `GET` | `/api/v1/notifications?user_id=` | In-app notification history |
| `POST` | `/api/v1/notifications/test` | Send a test notification (admin) |

Route responses include `start_lat`/`start_lon`, `end_lat`/`end_lon`, and a
`path` array of `[latitude, longitude]` points that follows roads. `path` is
`null` when no cached geometry exists, in which case the map falls back to a
straight line.

Admin endpoints require the `X-Admin-Token` header matching `ADMIN_API_TOKEN`.

## Surge formula

```
multiplier = min(1 + weather + accident + peak_hour, MAX_SURGE_MULTIPLIER)
fare       = round_to_nearest_10(base_fare × multiplier)
```

Default components:

| Trigger | Component | Notes |
| --- | --- | --- |
| Weather | `0.00 – 0.40` | Light rain 0.10, rain 0.20, heavy rain 0.30, thunderstorm 0.35, extreme heat/wind adjustments |
| Accident | `0.00 – 0.45` | Low 0.10, medium 0.20, high 0.35 per active report, capped |
| Rush hour | `0.20 / 0.25` | Weekdays 06:30–09:30 and 17:00–20:00 Africa/Nairobi |
| Cap | `2.50` | Configurable via `MAX_SURGE_MULTIPLIER` |

Surge events are refreshed every 5 minutes, persist their component breakdown and
reason, and expire after 30 minutes unless refreshed. Quotes lock the calculated
fare for 10 minutes.

## Notifications

`NOTIFICATION_PROVIDER=mock` (default) logs notifications and records delivery in
Postgres. Set `NOTIFICATION_PROVIDER=thrivewave` and configure one channel.

### ThriveVas SMS (default)

```env
THRIVEWAVE_CHANNEL=sms
THRIVEWAVE_BASE_URL=https://sms.thrivevas.com
THRIVEWAVE_SMS_PATH=/v1/message/send
THRIVEWAVE_SENDER_ID=ThriveVas
THRIVEWAVE_API_KEY=...
```

The adapter sends JSON to `POST /v1/message/send` with an `x-api-key` header and
`{"message", "msisdn", "sender_id"}`. SMS notifications use the user's `phone`
number, so each user must have a valid E.164 phone (`+2547...`). An optional
`THRIVEWAVE_CALLBACK_URL` enables DLR callbacks.

### ThrivePush web push

```env
THRIVEWAVE_CHANNEL=push
THRIVEWAVE_BASE_URL=https://thrivepush.io
THRIVEWAVE_NOTIFICATIONS_PATH=/api/personal-notifications
THRIVEWAVE_API_KEY=...
THRIVEWAVE_WEBSITE_ID=...
```

Push mode sends multipart form data with `website_id`, `subscriber_id`, `title`,
and `description`.

Notifications are deduplicated per user/event so scheduler runs do not spam users.
Delivery failures are stored with `status=failed` and the provider error.

See [docs/architecture.md](docs/architecture.md) for the full design, data model,
request flows, and production checklist.
