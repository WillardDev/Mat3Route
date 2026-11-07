"""
Database initialisation and seeding script.
Run with:
  python -m app.init_db
"""
import asyncio
import csv
import os
import traceback
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import AsyncSessionLocal, engine


def find_file(subpath: str) -> Path | None:
    """Search possible locations for schema/data files."""
    candidates = [
        Path(__file__).resolve().parent.parent / subpath,
        Path(__file__).resolve().parent.parent.parent / subpath,
        Path.cwd() / subpath,
        Path("/app") / subpath,
        Path("/app/backend") / subpath,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


async def run_schema(conn):
    schema_path = find_file("db/schema.sql")
    if not schema_path:
        print("[WARN] schema.sql not found; attempting tables creation via ORM")
        from .database import Base
        await conn.run_sync(Base.metadata.create_all)
        return

    print(f"  Applying schema from: {schema_path}")
    raw_sql = schema_path.read_text(encoding="utf-8")
    clean_stmts = []
    current: list[str] = []
    for line in raw_sql.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("--"):
            continue
        if trimmed.upper() in ("BEGIN;", "COMMIT;", "BEGIN", "COMMIT"):
            continue
        current.append(line)
        if trimmed.endswith(";"):
            clean_stmts.append("\n".join(current))
            current = []

    for stmt in clean_stmts:
        s = stmt.strip()
        if s:
            try:
                await conn.execute(text(s))
            except Exception as exc:
                print(f"  [schema stmt note]: {exc!r}")


async def seed_data(session: AsyncSession):
    csv_path = find_file("data/scraped_routes.csv")
    if not csv_path:
        print("[WARN] scraped_routes.csv not found; skipping seed.")
        return

    print(f"  Seeding data from: {csv_path}")
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"  Found {len(rows)} route records in CSV.")

    # 1. Upsert Route Lines
    distinct_lines = sorted({r["line"].strip() for r in rows if r.get("line")})
    for line_name in distinct_lines:
        await session.execute(
            text("INSERT INTO route_lines (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
            {"name": line_name},
        )
    await session.commit()

    line_map_res = await session.execute(text("SELECT id, name FROM route_lines"))
    line_map = {name: id_ for id_, name in line_map_res}

    # 2. Upsert SACCOs
    sacco_entries: dict[str, str] = {}
    for r in rows:
        code = r["sacco_code"].strip()
        name = r["sacco"].strip()
        if code not in sacco_entries:
            sacco_entries[code] = name

    for code, name in sacco_entries.items():
        await session.execute(
            text(
                "INSERT INTO saccos (name, code) VALUES (:name, :code) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name"
            ),
            {"name": name, "code": code},
        )
    await session.commit()

    sacco_map_res = await session.execute(text("SELECT id, code FROM saccos"))
    sacco_map = {code: id_ for id_, code in sacco_map_res}

    # 3. Upsert Routes
    upsert_route_sql = text("""
        INSERT INTO routes (
            line_id, route_number, start_location, end_location,
            sacco_id, fare_min, fare_max
        ) VALUES (
            :line_id, :route_number, :start_location, :end_location,
            :sacco_id, :fare_min, :fare_max
        )
        ON CONFLICT ON CONSTRAINT routes_unique
        DO UPDATE SET
            fare_min = EXCLUDED.fare_min,
            fare_max = EXCLUDED.fare_max,
            updated_at = now()
    """)

    for r in rows:
        line_id = line_map.get(r["line"].strip())
        sacco_id = sacco_map.get(r["sacco_code"].strip())
        if not line_id or not sacco_id:
            continue

        await session.execute(
            upsert_route_sql,
            {
                "line_id": line_id,
                "route_number": r["route_number"].strip(),
                "start_location": r["start"].strip(),
                "end_location": r["end"].strip(),
                "sacco_id": sacco_id,
                "fare_min": int(r["fare_min"]),
                "fare_max": int(r["fare_max"]),
            },
        )
    await session.commit()
    print("  Seed completed successfully.")


async def main():
    settings = get_settings()
    env_db = os.environ.get("DATABASE_URL", "NOT_SET")
    # Mask password for logs
    masked_env = env_db.split("@")[-1] if "@" in env_db else env_db
    print(f"=== Starting Mat3Route Database Initialisation ===")
    print(f"Target DB Host/DB: {masked_env}")
    print(f"Async URL Driver: {settings.async_database_url.split('://')[0]}")

    # Retry loop: wait up to 30s for Postgres cluster to accept connections on cold start
    max_retries = 6
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries}: connecting to database...")
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                print("Connection established. Running schema...")
                await run_schema(conn)
            print("Schema successfully verified/created.")

            async with AsyncSessionLocal() as session:
                await seed_data(session)
            print("=== Database Initialisation Complete ===")
            return
        except Exception as exc:
            print(f"[Attempt {attempt} failed]: {exc!r}")
            traceback.print_exc()
            if attempt < max_retries:
                await asyncio.sleep(4)

    print("[WARN] All DB connection attempts exhausted. Server will continue and retry on requests.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
