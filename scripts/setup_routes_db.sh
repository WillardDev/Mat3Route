#!/usr/bin/env bash
# Create the route database (if needed), apply the schema, and import the CSV.
#
# Usage:
#   scripts/setup_routes_db.sh [path/to/routes.csv]
#
# Environment:
#   DATABASE_URL  Full Postgres connection string. Defaults to postgresql:///mat3route_dev
#   DB_NAME       Database to create when DATABASE_URL is not set. Defaults to mat3route_dev

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CSV="${1:-$ROOT/data/scraped_routes.csv}"

if [[ ! -f "$CSV" ]]; then
  echo "CSV not found: $CSV" >&2
  exit 1
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  DB_URL="$DATABASE_URL"
else
  DB_NAME="${DB_NAME:-mat3route_dev}"
  DB_URL="postgresql:///$DB_NAME"

  if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
    echo "Creating database $DB_NAME..."
    createdb "$DB_NAME"
  fi
fi

echo "Applying schema..."
psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$ROOT/db/schema.sql"

echo "Importing $CSV..."
psql "$DB_URL" -v ON_ERROR_STOP=1 -v csv="$CSV" -f "$ROOT/db/import.sql"

psql "$DB_URL" -v ON_ERROR_STOP=1 -c "
  SELECT
    (SELECT count(*) FROM routes) AS routes,
    (SELECT count(*) FROM route_lines) AS lines,
    (SELECT count(*) FROM saccos) AS saccos;
"
