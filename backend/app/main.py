from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import accidents, health, notifications, quotes, routes, surges, users, weather
from .config import Settings, get_settings
from .db import Base, engine
from .scheduler import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if app_settings.auto_create_tables:
            logger.info("creating any missing database tables")
            Base.metadata.create_all(bind=engine)

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

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description=(
            "Weather alerts, dynamic fare surge calculation, accident reporting, "
            "and push notification delivery for Mat3 routes."
        ),
        lifespan=lifespan,
    )

    origins = app_settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api/v1")
    api.include_router(users.router)
    api.include_router(routes.router)
    api.include_router(weather.router)
    api.include_router(accidents.router)
    api.include_router(surges.router)
    api.include_router(quotes.router)
    api.include_router(notifications.router)

    app.include_router(health.router)
    app.include_router(api)
    return app


app = create_app()
