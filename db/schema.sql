-- Schema for Mat3 route information.
-- Safe to run repeatedly.

BEGIN;

CREATE TABLE IF NOT EXISTS route_lines (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saccos (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    code        text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routes (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    line_id         integer NOT NULL REFERENCES route_lines (id),
    route_number    text NOT NULL,
    start_location  text NOT NULL,
    end_location    text NOT NULL,
    sacco_id        integer NOT NULL REFERENCES saccos (id),
    fare_min        integer NOT NULL CHECK (fare_min >= 0),
    fare_max        integer NOT NULL CHECK (fare_max >= fare_min),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT routes_unique UNIQUE (line_id, route_number, start_location, end_location, sacco_id)
);

CREATE INDEX IF NOT EXISTS routes_route_number_idx ON routes (route_number);
CREATE INDEX IF NOT EXISTS routes_start_location_idx ON routes (start_location);
CREATE INDEX IF NOT EXISTS routes_end_location_idx ON routes (end_location);
CREATE INDEX IF NOT EXISTS routes_sacco_idx ON routes (sacco_id);

-- Convenient flat view of the route data.
CREATE OR REPLACE VIEW route_info AS
SELECT
    r.id,
    l.name AS line,
    r.route_number,
    r.start_location AS "start",
    r.end_location AS "end",
    s.name AS sacco,
    s.code AS sacco_code,
    r.fare_min,
    r.fare_max
FROM routes r
JOIN route_lines l ON l.id = r.line_id
JOIN saccos s ON s.id = r.sacco_id;

COMMIT;
