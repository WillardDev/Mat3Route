"""FastAPI application entry point for Mat3Route API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import get_settings
from .database import engine
from .models.schemas import HealthOut
from .routers import routes as routes_router
from .routers import sms as sms_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: test database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("[INFO] DB connection verified.")
    except Exception as exc:
        print(f"[WARN] DB ping on startup: {exc!r}")
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production REST API exposing Nairobi Matatu routes, stages, fares, and transport SACCOs "
        "from PostgreSQL, integrated with ThriveWave SMS API for credits and SMS alerts. "
        "Ready to be consumed by React and Angular frontends."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow React (localhost:3000, localhost:5173), Angular (localhost:4200), and all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(routes_router.router, prefix="/api/v1")
app.include_router(sms_router.router, prefix="/api/v1")


# ── Health & Root ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthOut, tags=["System"])
async def health():
    """Fly.io liveness probe and system health indicator."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"disconnected: {exc!r}"

    sms_status = "configured" if settings.thrivewave_api_key else "demo_simulation"
    return HealthOut(
        status="ok",
        version=settings.app_version,
        db=db_status,
        sms_service=sms_status,
    )


@app.get("/", tags=["System"])
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "health_check": "/health",
        "endpoints": {
            "routes": "/api/v1/routes",
            "lines": "/api/v1/routes/lines",
            "saccos": "/api/v1/routes/saccos",
            "stats": "/api/v1/routes/stats/summary",
            "search_locations": "/api/v1/routes/search/locations",
            "sms_credits": "/api/v1/sms/credits",
            "sms_send": "/api/v1/sms/send",
            "sms_send_route": "/api/v1/sms/send-route",
            "sms_pricing": "/api/v1/sms/pricing",
        },
    }
