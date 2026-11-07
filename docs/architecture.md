# Architecture — Weather Alerts & Dynamic Fare Surges

## 1. Goals

1. Detect significant weather changes for the service area and alert affected users before they book.
2. Adjust fares dynamically from three independent operational signals: weather, user-reported accidents, and peak rush hour.
3. Notify users proactively about weather and fare changes through a provider-agnostic push adapter (ThriveWave is the production adapter).
4. Keep accident reporting modular so a future verification/moderation workflow can replace the current stub.
5. Persist enough history to explain every fare change and audit every notification.

## 2. Component overview

```
                    ┌──────────────────────────────┐
                    │        APScheduler           │
                    │ weather poll / surge refresh │
                    │ surge expiry                 │
                    └──────────────┬───────────────┘
                                   │
┌──────────────┐      ┌────────────▼─────────────┐      ┌──────────────────┐
│ OpenWeather  │─────▶│     AutomationService    │─────▶│ NotificationService│
│     API      │      │  weather + surge + fanout│      │  dedupe + deliver │
└──────────────┘      └──────┬──────────┬────────┘      └────────┬─────────┘
                             │          │                        │
                     ┌───────▼───┐  ┌───▼────────┐        ┌──────▼────────┐
                     │WeatherSvc │  │ SurgeSvc   │        │ ThriveWave /  │
                     │ snapshots │  │ fare rules │        │ Mock provider │
                     └───────┬───┘  └───┬────────┘        └──────┬────────┘
                             │          │                        │
                             └──────────┴──────────┬─────────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │   PostgreSQL    │
                                          │ routes, users,  │
                                          │ weather, surges,│
                                          │ quotes, notices │
                                          └─────────────────┘
```

HTTP clients call the FastAPI routers. Routers depend on services through
FastAPI dependencies, so the weather client, notification provider, and database
session can be replaced in tests or production.

## 3. Data model

### Existing route tables

| Table | Purpose |
| --- | --- |
| `route_lines` | Route line names (A Line … Z Line) |
| `saccos` | SACCO names and codes |
| `routes` | Route number, start/end, SACCO, base fare range |

### New tables

| Table | Purpose |
| --- | --- |
| `app_users` | Commuters, optional home route, city and location |
| `notification_devices` | Push subscriber tokens / SMS phone numbers per user |
| `weather_snapshots` | Every OpenWeatherMap observation, including raw payload |
| `accident_reports` | User-reported route disruptions with severity/status |
| `surge_events` | Fare multiplier, component breakdown, reason, validity window |
| `fare_quotes` | Time-limited fare quotes shown before booking |
| `notifications` | In-app history and delivery status per user |

`surge_events` has a partial unique index that permits only one active surge per
route. `notifications.dedupe_key` is unique so repeated scheduler runs cannot
send the same alert twice. `notification_devices.token` stores the push
subscriber ID; SMS alerts are sent to the user's `app_users.phone` (E.164) while
the device row acts as the delivery opt-in.

## 4. Weather polling and change detection

The scheduler calls `AutomationService.poll_weather()` every
`WEATHER_POLL_MINUTES` (default 10):

1. Fetch current conditions from OpenWeatherMap using the configured Nairobi
   coordinates.
2. Load the previous snapshot for the same city.
3. Classify the new observation into a severity rank and a fare component.
4. Detect whether the change is significant.
5. Persist the snapshot.
6. If significant, notify active users in that city.
7. Recalculate surges for all routes.
8. If the change is not significant, still refresh surge events silently so
   existing weather surcharges stay alive and expire correctly.

### Weather assessment

| Condition | Severity | Component |
| --- | --- | --- |
| Clear / clouds | 0 | 0.00 |
| Drizzle / haze | 1 | 0.05 – 0.08 |
| Light rain | 2 | 0.10 |
| Rain | 3 | 0.20 |
| Heavy rain / snow | 4 | 0.30 |
| Thunderstorm / tornado / squall | 5 | 0.35 |
| Extreme heat (≥ 35 °C) | 2 | 0.15 – 0.25 |
| High wind (≥ 12 m/s) | 2 | +0.10 – 0.15 |

Components are capped at `WEATHER_MAX_COMPONENT` (default 0.40).

### Significant change rules

A change is significant when any of the following is true:

- Severe weather (severity ≥ 3) starts after non-severe conditions.
- Severity increases and the component rises by at least 0.05.
- Severe weather clears (notification direction `improved`).
- The weather component moves by at least 0.10 in either direction.

The first-ever snapshot is significant only when it is already severe, which
avoids alerting every user when the service is first deployed.

## 5. Dynamic fare engine

`SurgeService.compute()` combines independent signals:

```
raw = 1 + weather_component + accident_component + peak_component
multiplier = min(raw, MAX_SURGE_MULTIPLIER)
adjusted_fare = round_to_nearest_10(base_fare × multiplier)
```

- Weather component comes from the latest snapshot.
- Accident component sums weights for `reported`/`verified` reports inside the
  lookback window (default 120 minutes), capped at `ACCIDENT_MAX_COMPONENT`.
- Peak component applies on weekdays in `Africa/Nairobi` only:
  - 06:30–09:30 → `PEAK_MORNING_COMPONENT` (0.20)
  - 17:00–20:00 → `PEAK_EVENING_COMPONENT` (0.25)
- The final multiplier is capped (default 2.50).
- Fares are rounded to the nearest KSh 10, matching normal matatu pricing.

### Surge lifecycle

- `refresh_route()` computes the current state, reuses an existing event when the
  trigger and multiplier are effectively unchanged, and otherwise creates a new
  event while deactivating the previous one.
- Active events last `SURGE_TTL_MINUTES` (default 30).
- The scheduler refreshes all routes every `SURGE_REFRESH_MINUTES` (default 5).
- The expiry job deactivates events past `ends_at`.
- Every event stores the component breakdown and a human-readable reason, which
  is returned by the API and used in the notification body.

### Quotes

`POST /api/v1/quotes` computes the live fare and persists a `fare_quotes` row
valid for `QUOTE_TTL_MINUTES` (default 10). This is the product-level contract:
the user sees the current surge before booking, and the quote remains valid even
if the surge changes seconds later.

## 6. Accident reporting (modular stub)

`POST /api/v1/accidents` accepts a route, description, severity, optional user,
and coordinates. Creating a report:

1. Persists the report with `status=reported`.
2. Recalculates that route's surge.
3. Sends a route-disruption notification to subscribed users.

Admins can move a report through `verified`, `resolved`, or `rejected` with
`PATCH /api/v1/accidents/{id}/status`. Resolving or rejecting removes it from the
surge calculation on the next refresh.

Future integration points:

- Replace the open reporting endpoint with authenticated driver/passenger flows.
- Add duplicate clustering near the same coordinates and time window.
- Add photo evidence and moderation queues.
- Add a confidence score to weight verified versus unverified reports.
- Add a webhook/consumer for external traffic authorities.

## 7. Notifications

`NotificationService` handles fan-out and persistence:

1. Select active users by city (weather) or home route (surge/accident).
2. Build a dedupe key such as `surge:{route}:{multiplier}:{user}:{hour}`.
3. Skip users whose dedupe key already exists.
4. Send through the configured provider to every active device.
5. Persist `sent`, `failed`, or `skipped` with the provider message ID or error.

### Providers

- `MockNotificationProvider` — local development; logs and records messages.
- `ThriveWaveProvider` — production adapter, configurable channel:
  - `sms` (default): ThriveVas SMS. JSON request to
    `https://sms.thrivevas.com/v1/message/send` with an `x-api-key` header and
    `message`, `msisdn`, `sender_id` (plus an optional `callback_url`). The
    recipient is the user's E.164 phone number.
  - `push`: ThrivePush-style multipart request to
    `/api/personal-notifications` with `website_id`, `subscriber_id`, `title`,
    `description`.

If `NOTIFICATION_PROVIDER=thrivewave` but no API key is set, the factory falls
back to the mock provider and logs a warning. This keeps local development
working without credentials.

## 8. Scheduler

APScheduler runs three jobs in-process:

| Job | Default interval | Action |
| --- | --- | --- |
| `weather_poll` | 10 minutes | Fetch weather, detect changes, notify, refresh surges |
| `surge_refresh` | 5 minutes | Recompute all route surges and notify on meaningful changes |
| `surge_expiry` | 1 minute | Deactivate expired surge events |

Jobs use `max_instances=1` and `coalesce=True` to avoid overlapping runs after a
slow API call. Weather polling is skipped at startup if no OpenWeatherMap key is
configured.

For multi-instance deployments, replace the in-process scheduler with a single
worker/cron job or a distributed scheduler (Celery beat, Cloud Scheduler, etc.)
so only one instance polls and sends.

## 9. HTTP API and security

- Public endpoints: users/devices, routes/fares, quotes, weather history,
  accident reporting, notification history.
- Admin endpoints (`X-Admin-Token`): weather refresh, surge recalculation,
  surge expiry, accident status changes, test notifications.
- `GET /health` reports DB status and whether weather/ThriveWave are configured.
- `GET /map` serves the static Leaflet live map.
- OpenAPI/Swagger is available at `/docs`.

### Live map

`backend/app/static/live-map.html` is a dependency-free Leaflet page served at
`/map`. It reads the existing public API:

- `GET /api/v1/routes?limit=200` for routes, stage coordinates, and road paths.
- `GET /api/v1/accidents?limit=200` for incident markers.
- `GET /api/v1/routes/{id}/fare` when a route is selected.

Each route includes a `path` array of `[latitude, longitude]` points. Paths are
cached OSRM driving directions between the geocoded start/end stages in
`backend/app/data/route_geometry.json`, generated once by
`scripts/fetch_route_geometry.py`. They follow roads but are fastest-driving
routes rather than guaranteed sacco corridors. If a path is missing, the map
falls back to a straight line between the two stages.

Stage coordinates live in `backend/app/data/nairobi_locations.json`, generated
by `scripts/geocode_locations.py` using OpenStreetMap Nominatim. Incidents
without `latitude`/`longitude` fall back to the route start stage and are
labelled "approximate" in the popup.

The page refreshes incidents every 30 seconds and only reloads route geometry on
load or manual refresh, so open route popups are not disturbed by the timer. OSM
raster tiles require attribution; the public tile server is for development only
and should be replaced by a production tile provider or self-hosted tiles. OSRM's
demo server is likewise for development and one-off caching only; self-host OSRM
or use a commercial routing provider in production.

Before production:

- Put the API behind HTTPS and a reverse proxy.
- Replace the shared admin token with role-based auth (OAuth2/JWT).
- Add rate limiting to accident reporting and quote creation.
- Restrict CORS to known frontend origins (`CORS_ORIGINS`).
- Add device token rotation and removal on logout.

## 10. Failure handling

- OpenWeatherMap failures surface as HTTP 502 on manual refresh and are logged
  by the scheduler; the previous snapshot remains available.
- ThriveWave failures are stored per notification with `status=failed` and the
  error message. One failing device does not block other users.
- Missing devices produce `status=skipped` rather than dropping the in-app record.
- A failed surge refresh rolls back the session in the scheduler job, leaving the
  last active surge intact.
- Dedupe keys protect against duplicate alerts across scheduler retries.

## 11. Configuration reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql:///mat3route_dev` | PostgreSQL connection string |
| `OPENWEATHER_API_KEY` | — | OpenWeatherMap API key |
| `OPENWEATHER_CITY` | `Nairobi` | City label stored with snapshots |
| `OPENWEATHER_LATITUDE` / `LONGITUDE` | Nairobi | Polling coordinates |
| `WEATHER_POLL_MINUTES` | `10` | Weather polling interval |
| `NOTIFICATION_PROVIDER` | `mock` | `mock` or `thrivewave` |
| `THRIVEWAVE_CHANNEL` | `sms` | `sms` (ThriveVas) or `push` (ThrivePush) |
| `THRIVEWAVE_BASE_URL` | `https://sms.thrivevas.com` | Provider base URL |
| `THRIVEWAVE_SMS_PATH` | `/v1/message/send` | ThriveVas SMS endpoint |
| `THRIVEWAVE_SENDER_ID` | `ThriveVas` | Registered sender ID |
| `THRIVEWAVE_CALLBACK_URL` | — | Optional DLR callback URL |
| `THRIVEWAVE_API_KEY` | — | Provider API key (sent as `x-api-key` for SMS) |
| `THRIVEWAVE_WEBSITE_ID` | — | ThrivePush website/subscriber scope |
| `SURGE_REFRESH_MINUTES` | `5` | Surge recalculation interval |
| `SURGE_TTL_MINUTES` | `30` | Active surge lifetime |
| `MAX_SURGE_MULTIPLIER` | `2.5` | Hard cap on surges |
| `ACCIDENT_LOOKBACK_MINUTES` | `120` | Accident influence window |
| `QUOTE_TTL_MINUTES` | `10` | Fare quote validity |
| `ADMIN_API_TOKEN` | `dev-admin-token` | Admin header value |
| `SCHEDULER_ENABLED` | `true` | Enable in-process scheduler |
| `AUTO_CREATE_TABLES` | `true` | Create missing tables on startup |
| `TIMEZONE` | `Africa/Nairobi` | Peak-hour timezone |
| `CORS_ORIGINS` | `*` | Comma-separated allowed frontend origins |

## 12. Testing

The test suite uses an in-memory SQLite database and FastAPI dependency
overrides:

- Pure rule tests for weather assessment, change detection, peak windows, and
  fare rounding.
- API lifecycle tests for users/devices, accidents → surge → quote →
  notification, weather refresh, admin auth, and accident status changes.
- ThriveWave adapter tests using a mocked HTTP transport.

Run with:

```bash
cd backend && ../.venv/bin/pytest
```
