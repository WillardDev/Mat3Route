from __future__ import annotations


def auth_headers(client, phone: str = "+254700000123") -> dict[str, str]:
    client.post("/api/auth/otp/request", json={"phone": phone})
    verified = client.post("/api/auth/otp/verify", json={"phone": phone, "code": "4729"})
    assert verified.status_code == 200, verified.text
    return {"Authorization": f"Bearer {verified.json()['access']}"}


def test_routes_list_uses_frontend_shape(client, route):
    response = client.get("/api/routes")
    assert response.status_code == 200, response.text
    routes = response.json()
    item = next(r for r in routes if r["id"] == route.id)
    assert item["number"] == "100"
    assert item["name"] == "Nairobi CBD → Kiambu"
    assert item["via"] == "A Line"
    assert item["destination"] == "Kiambu"
    assert item["pill"] in {"maji_safi", "moderate", "kwama"}
    assert item["alert_count"] == 0
    assert item["subscribed"] is False


def test_route_detail_has_saccos_events_and_stages(client, route):
    response = client.get(f"/api/routes/{route.id}")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["stages"] == ["Nairobi CBD", "Kiambu"]
    assert len(detail["saccos"]) == 1
    sacco = detail["saccos"][0]
    assert sacco["name"] == "Super Metro"
    assert sacco["usual_fare"] == 80
    assert sacco["state"] == "normal"
    assert detail["events"] == []
    assert detail["banner"] is None
    assert detail["updated_at"]


def test_report_vote_and_verification_flow(client, route):
    detail = client.get(f"/api/routes/{route.id}").json()
    sacco_id = detail["saccos"][0]["id"]
    author = auth_headers(client, "+254700000111")

    created = client.post(
        "/api/reports",
        json={
            "route": route.id,
            "type": "fare_hike",
            "fare": 100,
            "sacco": sacco_id,
            "note": "fare ni 100 sasa",
        },
        headers=author,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    event = body["event"]
    assert event["type"] == "fare_hike"
    assert event["confirmations"] == 1
    assert event["needed"] == 2
    assert event["status"] == "pending"
    assert event["i_reported"] is True
    assert event["my_vote"] == "still"

    detail = client.get(f"/api/routes/{route.id}", headers=author).json()
    assert detail["events"][0]["id"] == event["id"]
    assert detail["saccos"][0]["state"] == "pending"
    assert detail["saccos"][0]["fare"] == 100

    for phone in ("+254700000112", "+254700000113"):
        headers = auth_headers(client, phone)
        voted = client.post(
            f"/api/events/{event['id']}/vote", json={"kind": "still"}, headers=headers
        )
        assert voted.status_code == 200, voted.text
        assert voted.json()["my_vote"] == "still"

    refreshed = client.get(f"/api/routes/{route.id}", headers=author).json()
    verified = refreshed["events"][0]
    assert verified["status"] == "verified"
    assert verified["confirmations"] == 3
    assert verified["needed"] == 0
    assert refreshed["saccos"][0]["state"] == "up"
    assert refreshed["banner"]["event_id"] == event["id"]


def test_subscribe_toggle(client, route):
    headers = auth_headers(client, "+254700000222")
    first = client.post(f"/api/routes/{route.id}/subscribe", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"subscribed": True}
    assert client.get(f"/api/routes/{route.id}", headers=headers).json()["subscribed"] is True
    listed = next(r for r in client.get("/api/routes", headers=headers).json() if r["id"] == route.id)
    assert listed["subscribed"] is True

    second = client.post(f"/api/routes/{route.id}/subscribe", headers=headers)
    assert second.json() == {"subscribed": False}


def test_signal_has_funnel_reports_and_alerts(client):
    response = client.get("/api/signal")
    assert response.status_code == 200, response.text
    signal = response.json()
    assert set(signal["funnel"]) == {"raw", "spam", "events", "verified"}
    assert signal["funnel"]["raw"] == signal["funnel"]["spam"] + signal["funnel"]["events"]
    assert isinstance(signal["reports"], list)
    assert isinstance(signal["verified_events"], list)
    assert isinstance(signal["alerts"], list)
    assert isinstance(signal["pending_count"], int)


def test_report_requires_sign_in(client, route):
    response = client.post("/api/reports", json={"route": route.id, "type": "jam"})
    assert response.status_code == 401
