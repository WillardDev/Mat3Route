-- Weather alerts, dynamic fare surge, accident reporting, and notification tables.
-- Safe to run repeatedly. Apply after db/schema.sql.

BEGIN;

CREATE TABLE IF NOT EXISTS app_users (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    phone       text NOT NULL UNIQUE,
    name        text,
    email       text,
    city        text NOT NULL DEFAULT 'Nairobi',
    latitude    double precision,
    longitude   double precision,
    route_id    integer REFERENCES routes (id) ON DELETE SET NULL,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_devices (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     integer NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    provider    text NOT NULL DEFAULT 'thrivewave',
    token       text NOT NULL,
    platform    text,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT notification_devices_provider_token_key UNIQUE (provider, token)
);

CREATE INDEX IF NOT EXISTS notification_devices_user_idx
    ON notification_devices (user_id);

CREATE TABLE IF NOT EXISTS weather_snapshots (
    id                  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city                text NOT NULL,
    latitude            double precision NOT NULL,
    longitude           double precision NOT NULL,
    condition_code      integer,
    condition_main      text NOT NULL,
    description         text NOT NULL,
    temperature_c       double precision NOT NULL,
    feels_like_c        double precision NOT NULL,
    humidity            integer,
    wind_speed_mps      double precision,
    observed_at         timestamptz NOT NULL,
    fetched_at          timestamptz NOT NULL DEFAULT now(),
    raw                 jsonb
);

CREATE INDEX IF NOT EXISTS weather_snapshots_city_fetched_idx
    ON weather_snapshots (city, fetched_at);

CREATE TABLE IF NOT EXISTS accident_reports (
    id                  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_id            integer NOT NULL REFERENCES routes (id) ON DELETE CASCADE,
    reported_by_user_id integer REFERENCES app_users (id) ON DELETE SET NULL,
    description         text NOT NULL,
    severity            text NOT NULL DEFAULT 'medium',
    status              text NOT NULL DEFAULT 'reported',
    latitude            double precision,
    longitude           double precision,
    reported_at         timestamptz NOT NULL DEFAULT now(),
    resolved_at         timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT accident_reports_severity_check
        CHECK (severity IN ('low', 'medium', 'high')),
    CONSTRAINT accident_reports_status_check
        CHECK (status IN ('reported', 'verified', 'resolved', 'rejected'))
);

CREATE INDEX IF NOT EXISTS accident_reports_route_reported_idx
    ON accident_reports (route_id, reported_at DESC);
CREATE INDEX IF NOT EXISTS accident_reports_status_idx
    ON accident_reports (status);

CREATE TABLE IF NOT EXISTS surge_events (
    id                  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_id            integer REFERENCES routes (id) ON DELETE CASCADE,
    trigger_type        text NOT NULL,
    multiplier          double precision NOT NULL,
    weather_component   double precision NOT NULL DEFAULT 0,
    accident_component  double precision NOT NULL DEFAULT 0,
    peak_component      double precision NOT NULL DEFAULT 0,
    base_fare_min       integer NOT NULL,
    base_fare_max       integer NOT NULL,
    adjusted_fare_min   integer NOT NULL,
    adjusted_fare_max   integer NOT NULL,
    reason              text NOT NULL,
    starts_at           timestamptz NOT NULL,
    ends_at             timestamptz NOT NULL,
    is_active           boolean NOT NULL DEFAULT true,
    weather_snapshot_id integer REFERENCES weather_snapshots (id) ON DELETE SET NULL,
    accident_report_id  integer REFERENCES accident_reports (id) ON DELETE SET NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT surge_events_trigger_type_check
        CHECK (trigger_type IN ('weather', 'accident', 'peak_hour', 'combined', 'manual')),
    CONSTRAINT surge_events_multiplier_check CHECK (multiplier >= 1.0)
);

CREATE INDEX IF NOT EXISTS surge_events_route_active_idx
    ON surge_events (route_id, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS surge_events_one_active_per_route
    ON surge_events (route_id)
    WHERE is_active AND route_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS fare_quotes (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         integer REFERENCES app_users (id) ON DELETE SET NULL,
    route_id        integer NOT NULL REFERENCES routes (id) ON DELETE CASCADE,
    surge_event_id  integer REFERENCES surge_events (id) ON DELETE SET NULL,
    multiplier      double precision NOT NULL,
    base_fare_min   integer NOT NULL,
    base_fare_max   integer NOT NULL,
    fare_min        integer NOT NULL,
    fare_max        integer NOT NULL,
    quoted_at       timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS fare_quotes_user_idx ON fare_quotes (user_id, quoted_at DESC);
CREATE INDEX IF NOT EXISTS fare_quotes_route_idx ON fare_quotes (route_id, quoted_at DESC);

CREATE TABLE IF NOT EXISTS notifications (
    id                  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             integer NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    notification_type   text NOT NULL,
    weather_snapshot_id integer REFERENCES weather_snapshots (id) ON DELETE SET NULL,
    surge_event_id      integer REFERENCES surge_events (id) ON DELETE SET NULL,
    accident_report_id  integer REFERENCES accident_reports (id) ON DELETE SET NULL,
    title               text NOT NULL,
    body                text NOT NULL,
    provider            text NOT NULL,
    provider_message_id text,
    status              text NOT NULL DEFAULT 'pending',
    dedupe_key          text UNIQUE,
    error               text,
    payload             jsonb,
    sent_at             timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT notifications_type_check
        CHECK (notification_type IN ('weather', 'surge', 'accident', 'system')),
    CONSTRAINT notifications_status_check
        CHECK (status IN ('pending', 'sent', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS notifications_user_created_idx
    ON notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS notifications_status_idx
    ON notifications (status);

COMMIT;
