-- Import scraped routes from a CSV file.
-- Expects the psql variable `csv` to point to the CSV file, e.g.:
--   psql "$DATABASE_URL" -v csv=/path/to/scraped_routes.csv -f db/import.sql
-- The import is idempotent: existing routes have their fares updated.

BEGIN;

CREATE TEMP TABLE route_import (
    line          text NOT NULL,
    route_number  text NOT NULL,
    "start"       text NOT NULL,
    "end"         text NOT NULL,
    sacco         text NOT NULL,
    sacco_code    text NOT NULL,
    fare_min      integer NOT NULL,
    fare_max      integer NOT NULL
) ON COMMIT DROP;

\copy route_import (line, route_number, "start", "end", sacco, sacco_code, fare_min, fare_max) FROM :'csv' WITH (FORMAT csv, HEADER true)

INSERT INTO route_lines (name)
SELECT DISTINCT line
FROM route_import
ON CONFLICT (name) DO NOTHING;

INSERT INTO saccos (name, code)
SELECT DISTINCT ON (sacco_code) sacco, sacco_code
FROM route_import
ORDER BY sacco_code
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO routes (
    line_id,
    route_number,
    start_location,
    end_location,
    sacco_id,
    fare_min,
    fare_max
)
SELECT
    l.id,
    i.route_number,
    i."start",
    i."end",
    s.id,
    i.fare_min,
    i.fare_max
FROM route_import i
JOIN route_lines l ON l.name = i.line
JOIN saccos s ON s.code = i.sacco_code
ON CONFLICT ON CONSTRAINT routes_unique
DO UPDATE SET
    fare_min = EXCLUDED.fare_min,
    fare_max = EXCLUDED.fare_max,
    updated_at = now();

COMMIT;
