"""FastAPI application entry point for Mat3Route API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api import (
    accidents,
    community,
    live_map,
    notifications,
    quotes,
    routes as api_routes,
    surges,
    users,
    weather,
)
from .config import Settings, get_settings
from .database import engine as async_engine
from .db import Base as SyncBase
from .db import SessionLocal, engine as sync_engine
from .routers import auth as auth_router
from .routers import sms as sms_router
from .scheduler import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# httpx logs full request URLs; OpenWeather takes its API key as a query param,
# so keep those logs at WARNING to avoid writing secrets to disk.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Async stack (routes + SMS) health check
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("DB connection verified")
        except Exception as exc:
            logger.warning("DB ping on startup: %r", exc)

        # Sync stack (weather, surges, accidents, notifications)
        if app_settings.auto_create_tables:
            logger.info("creating any missing database tables")
            SyncBase.metadata.create_all(bind=sync_engine)
            try:
                with SessionLocal() as db:
                    community.seed_demo_events(db)
            except Exception as exc:  # seeding must never block startup
                logger.warning("community demo seed skipped: %r", exc)

        scheduler = None
        if app_settings.scheduler_enabled:
            scheduler = build_scheduler(app_settings)
            scheduler.start()
            logger.info(
                "scheduler started: weather every %s min, surges every %s min",
                app_settings.weather_poll_minutes,
                app_settings.surge_refresh_minutes,
            )

        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)
                logger.info("scheduler stopped")
            await async_engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description=(
            "Mat3Route backend: Nairobi matatu routes, fares, weather alerts, "
            "dynamic fare surges, accident reporting, SMS notifications, and a "
            "live OpenStreetMap view."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=app_settings.cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    api = APIRouter(prefix="/api/v1")
    api.include_router(api_routes.router)
    api.include_router(accidents.router)
    api.include_router(weather.router)
    api.include_router(surges.router)
    api.include_router(quotes.router)
    api.include_router(notifications.router)
    api.include_router(users.router)
    api.include_router(sms_router.router)

    app.include_router(live_map.router)
    app.include_router(api)
    # The MatatuPulse frontend calls /api/auth/* and /api/* (no /v1 segment).
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(community.router, prefix="/api")

    # ── Health & Root ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health() -> dict:
        """Fly.io liveness probe and system health indicator."""
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:
            db_status = f"disconnected: {exc!r}"

        if not app_settings.sms_enabled:
            sms_status = "disabled"
        elif app_settings.thrivewave_api_key:
            sms_status = "configured"
        else:
            sms_status = "demo_simulation"

        provider = app_settings.notification_provider.lower()
        return {
            "status": "ok" if db_status == "connected" else "degraded",
            "version": "0.1.0",
            "db": db_status,
            "database": "ok" if db_status == "connected" else "unavailable",
            "sms_service": sms_status,
            "sms_enabled": app_settings.sms_enabled,
            "weather_configured": bool(app_settings.openweather_api_key),
            "thrivewave_configured": bool(app_settings.thrivewave_api_key),
            "notification_provider": app_settings.notification_provider,
            "notification_channel": (
                app_settings.thrivewave_channel.lower()
                if provider == "thrivewave"
                else "mock"
            ),
            "scheduler_enabled": app_settings.scheduler_enabled,
        }

    @app.get("/", tags=["System"])
    async def root() -> dict:
        return {
            "service": app_settings.app_name,
            "version": "0.1.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
            "health_check": "/health",
            "live_map": "/map",
            "endpoints": {
                "routes": "/api/v1/routes",
                "route_fare": "/api/v1/routes/{route_id}/fare",
                "accidents": "/api/v1/accidents",
                "weather": "/api/v1/weather/current",
                "surges": "/api/v1/surges",
                "quotes": "/api/v1/quotes",
                "notifications": "/api/v1/notifications",
                "users": "/api/v1/users",
                "sms_credits": "/api/v1/sms/credits",
                "sms_send": "/api/v1/sms/send",
                "sms_send_route": "/api/v1/sms/send-route",
                "sms_pricing": "/api/v1/sms/pricing",
            },
        }

    return app


app = create_app()
