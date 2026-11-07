from __future__ import annotations

import pytest

ADMIN = {"X-Admin-Token": "test-admin"}


def create_user(client, route_id: int, phone: str = "+254700000001", token: str = "token-1"):
    response = client.post(
        "/api/v1/users",
        json={
            "phone": phone,
            "name": "Test Commuter",
            "city": "Nairobi",
            "route_id": route_id,
        },
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    response = client.post(
        f"/api/v1/users/{user_id}/devices",
        json={"provider": "thrivewave", "token": token, "platform": "web"},
    )
    assert response.status_code == 201, response.text
    return user_id


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["weather_configured"] is True


def test_user_and_device_registration(client, route):
    user_id = create_user(client, route.id)
    assert client.get(f"/api/v1/users/{user_id}").status_code == 200
    assert len(client.get(f"/api/v1/users/{user_id}/devices").json()) == 1

    duplicate = client.post(
        "/api/v1/users",
        json={"phone": "+254700000001", "city": "Nairobi"},
    )
    assert duplicate.status_code == 409


def test_route_list_and_fare_preview(client, route):
    listing = client.get("/api/v1/routes", params={"line": "A Line"})
    assert listing.status_code == 200
    first = listing.json()[0]
    assert first["route_number"] == "100"
    assert first["start_lat"] == pytest.approx(-1.29003, abs=1e-5)
    assert first["start_lon"] == pytest.approx(36.82497, abs=1e-5)
    assert first["end_lat"] is not None
    assert first["end_lon"] is not None

    path = first["path"]
    assert isinstance(path, list)
    assert len(path) > 2
    assert path[0][0] == pytest.approx(first["start_lat"], abs=0.02)
    assert path[0][1] == pytest.approx(first["start_lon"], abs=0.02)
    assert path[-1][0] == pytest.approx(first["end_lat"], abs=0.02)
    assert path[-1][1] == pytest.approx(first["end_lon"], abs=0.02)

    fare = client.get(f"/api/v1/routes/{route.id}/fare")
    assert fare.status_code == 200
    body = fare.json()
    assert body["base_fare_min"] == 80
    assert body["fare_min"] >= 80


def test_live_map_page_is_served(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "OpenStreetMap" in response.text
    assert "leaflet" in response.text.lower()


def test_accident_triggers_surge_quote_and_notification(client, route, provider):
    user_id = create_user(client, route.id)

    response = client.post(
        "/api/v1/accidents",
        json={
            "route_id": route.id,
            "reported_by_user_id": user_id,
            "description": "Matatu collision blocking the road",
            "severity": "high",
        },
    )
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]

    surges = client.get("/api/v1/surges", params={"route_id": route.id})
    assert surges.status_code == 200
    assert surges.json(), "an active surge should be created"
    assert surges.json()[0]["multiplier"] > 1.0
    assert surges.json()[0]["accident_component"] >= 0.35

    quote = client.post(
        "/api/v1/quotes",
        json={"route_id": route.id, "user_id": user_id},
    )
    assert quote.status_code == 201, quote.text
    quote_body = quote.json()
    assert quote_body["multiplier"] > 1.0
    assert quote_body["fare_min"] >= 80

    notifications = client.get(
        "/api/v1/notifications", params={"user_id": user_id}
    )
    assert notifications.status_code == 200
    types = {item["notification_type"] for item in notifications.json()}
    assert "accident" in types
    assert any(item["status"] == "sent" for item in notifications.json())
    assert provider.sent

    verified = client.patch(
        f"/api/v1/accidents/{report_id}/status",
        json={"status": "verified"},
        headers=ADMIN,
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"

    resolved = client.patch(
        f"/api/v1/accidents/{report_id}/status",
        json={"status": "resolved"},
        headers=ADMIN,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_weather_refresh_detects_change_and_notifies(client, route, weather_client):
    user_id = create_user(client, route.id, phone="+254700000009", token="token-9")
    weather_client.set_condition(
        "Thunderstorm",
        "thunderstorm with heavy rain",
        temperature_c=19.0,
        wind_speed_mps=14.0,
        condition_code=211,
    )

    response = client.post("/api/v1/weather/refresh", headers=ADMIN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["significant_change"] is True
    assert body["direction"] == "worsened"

    current = client.get("/api/v1/weather/current")
    assert current.status_code == 200
    assert current.json()["condition_main"] == "Thunderstorm"

    notifications = client.get(
        "/api/v1/notifications", params={"user_id": user_id}
    ).json()
    assert any(item["notification_type"] == "weather" for item in notifications)


def test_admin_endpoints_require_token(client, route):
    assert client.post("/api/v1/surges/recalculate").status_code == 401

    response = client.post("/api/v1/surges/recalculate", headers=ADMIN)
    assert response.status_code == 200, response.text
    assert response.json()["routes_evaluated"] == 1
