from __future__ import annotations

from app.locations import coordinates_for, load_locations
from app.route_geometry import geometry_for, load_route_geometry


def test_all_route_locations_have_coordinates():
    locations = load_locations()
    assert len(locations) == 88
    for name, (latitude, longitude) in locations.items():
        assert -5.0 < latitude < 1.0, name
        assert 33.0 < longitude < 42.0, name


def test_all_route_pairs_have_road_geometry():
    geometry = load_route_geometry()
    assert len(geometry) == 88
    for key, path in geometry.items():
        start, end = key.split("|", 1)
        assert start and end
        assert len(path) >= 2, key
        for latitude, longitude in path:
            assert -5.0 < latitude < 1.0, key
            assert 33.0 < longitude < 42.0, key


def test_known_and_unknown_locations():
    nairobi = coordinates_for("Nairobi CBD")
    assert nairobi is not None
    assert -1.31 < nairobi[0] < -1.27
    assert 36.80 < nairobi[1] < 36.85

    kiambu = coordinates_for("Kiambu")
    assert kiambu is not None
    assert -1.20 < kiambu[0] < -1.10

    assert coordinates_for("Definitely not a stage") is None
    assert coordinates_for(None) is None


def test_known_and_unknown_route_geometry():
    path = geometry_for("Nairobi CBD", "Kiambu")
    assert path is not None
    assert len(path) > 10
    assert geometry_for("Nairobi CBD", "Definitely not a stage") is None
    assert geometry_for(None, "Kiambu") is None
