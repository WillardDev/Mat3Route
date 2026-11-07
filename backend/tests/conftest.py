from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register models with Base.metadata
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.dependencies import get_notification_provider, get_weather_client
from app.main import create_app
from app.models import Route, RouteLine, Sacco
from app.providers.mock import MockNotificationProvider
from app.services.weather import WeatherReading


class FakeWeatherClient:
    def __init__(self) -> None:
        self.reading = WeatherReading(
            city="Nairobi",
            latitude=-1.2921,
            longitude=36.8219,
            condition_code=800,
            condition_main="Clear",
            description="clear sky",
            temperature_c=24.0,
            feels_like_c=24.0,
            humidity=50,
            wind_speed_mps=2.0,
            observed_at=datetime.now(UTC),
            raw={"weather": [{"main": "Clear", "description": "clear sky"}]},
        )

    def set_condition(
        self,
        main: str,
        description: str,
        temperature_c: float = 22.0,
        wind_speed_mps: float = 2.0,
        condition_code: int = 500,
    ) -> None:
        self.reading = replace(
            self.reading,
            condition_main=main,
            description=description,
            temperature_c=temperature_c,
            wind_speed_mps=wind_speed_mps,
            condition_code=condition_code,
            observed_at=datetime.now(UTC),
        )

    def fetch_current(self, **_: object) -> WeatherReading:
        return replace(self.reading, observed_at=datetime.now(UTC))


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        auto_create_tables=False,
        scheduler_enabled=False,
        admin_api_token="test-admin",
        notification_provider="mock",
        sms_enabled=False,
        openweather_api_key="test-key",
        openweather_city="Nairobi",
        timezone="Africa/Nairobi",
    )


@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db(engine) -> Session:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def route(db: Session) -> Route:
    line = RouteLine(name="A Line")
    sacco = Sacco(name="Super Metro", code="SM")
    db.add_all([line, sacco])
    db.flush()
    route = Route(
        line_id=line.id,
        sacco_id=sacco.id,
        route_number="100",
        start_location="Nairobi CBD",
        end_location="Kiambu",
        fare_min=80,
        fare_max=120,
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@pytest.fixture
def provider() -> MockNotificationProvider:
    return MockNotificationProvider()


@pytest.fixture
def weather_client() -> FakeWeatherClient:
    return FakeWeatherClient()


@pytest.fixture
def client(settings, db, provider, weather_client):
    application = create_app(settings)

    def override_db():
        yield db

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_notification_provider] = lambda: provider
    application.dependency_overrides[get_weather_client] = lambda: weather_client

    with TestClient(application) as test_client:
        yield test_client
