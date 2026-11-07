# Mat3Route

Matatu route information stored in PostgreSQL.

## Database setup

Requires PostgreSQL (`psql`, `createdb`) on your PATH.

```bash
./scripts/setup_routes_db.sh
```

The script:

1. Creates the `mat3route_dev` database if it does not exist.
2. Applies `db/schema.sql`.
3. Imports `data/scraped_routes.csv`.

It is safe to re-run; existing routes are updated rather than duplicated.

To use a different database or a remote server:

```bash
DATABASE_URL="postgresql://user:pass@host:5432/mydb" ./scripts/setup_routes_db.sh
# or, for a local database with a different name:
DB_NAME=mat3route_test ./scripts/setup_routes_db.sh
```

You can also pass a different CSV file as the first argument:

```bash
./scripts/setup_routes_db.sh path/to/routes.csv
```

## Schema

- `route_lines` — matatu line names (A Line … Z Line).
- `saccos` — SACCO names and codes.
- `routes` — one row per route with start/end locations, SACCO, and fare range.
- `route_info` — a flat view joining all three tables.

## Environment

The local development credentials live in `.env` (ignored by git). A committed
template is available in `.env.example`:

```bash
cp .env.example .env   # then fill in the password
```

The app role is `mat3route` and the database is `mat3route_dev`:

```
DATABASE_URL=postgresql://mat3route:<password>@localhost:5432/mat3route_dev
```

Load it in your shell with:

```bash
set -a; source .env; set +a
```

Note: `scripts/setup_routes_db.sh` should keep using your Postgres admin account
(the default local connection), since it creates the database and schema.

## Connecting

```bash
psql mat3route_dev            # local admin
psql "$DATABASE_URL"          # app role from .env
```

## Example queries

Routes departing from Nairobi CBD:

```sql
SELECT line, route_number, "start", "end", sacco, fare_min, fare_max
FROM route_info
WHERE "start" = 'Nairobi CBD'
ORDER BY line, route_number;
```

Cheapest routes:

```sql
SELECT line, route_number, "start", "end", sacco, fare_min
FROM route_info
ORDER BY fare_min, fare_max
LIMIT 10;
```

Routes by SACCO:

```sql
SELECT sacco, count(*) AS routes
FROM route_info
GROUP BY sacco
ORDER BY routes DESC;
```
