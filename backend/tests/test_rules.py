from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services.fare_rules import apply_multiplier, peak_component, round_fare
from app.services.weather_rules import assess, detect_change


def weather(main: str, description: str, temperature: float = 22.0, wind: float = 2.0):
    return SimpleNamespace(
        condition_main=main,
        description=description,
        temperature_c=temperature,
        wind_speed_mps=wind,
    )


def test_weather_components_by_condition():
    assert assess(weather("Clear", "clear sky")).component == 0.0
    assert assess(weather("Rain", "heavy intensity rain")).component == 0.30
    assert assess(weather("Thunderstorm", "thunderstorm with rain")).component == 0.35
    assert assess(weather("Clear", "clear sky", temperature=38.0)).component > 0.15
    assert assess(weather("Clear", "clear sky", wind=18.0)).component >= 0.15


def test_weather_change_detection():
    clear = weather("Clear", "clear sky")
    heavy_rain = weather("Rain", "heavy intensity rain")

    worsening = detect_change(heavy_rain, clear)
    assert worsening.significant is True
    assert worsening.direction == "worsened"

    improvement = detect_change(clear, heavy_rain)
    assert improvement.significant is True
    assert improvement.direction == "improved"

    assert detect_change(clear, clear).significant is False
    assert detect_change(heavy_rain, None).significant is True


def test_peak_hour_windows():
    tz = "Africa/Nairobi"
    monday_morning = datetime(2026, 11, 2, 7, 30, tzinfo=ZoneInfo(tz))
    monday_evening = datetime(2026, 11, 2, 18, 0, tzinfo=ZoneInfo(tz))
    monday_midday = datetime(2026, 11, 2, 12, 0, tzinfo=ZoneInfo(tz))
    saturday_evening = datetime(2026, 11, 7, 18, 0, tzinfo=ZoneInfo(tz))

    assert peak_component(monday_morning, tz, 0.20, 0.25) == (0.20, "morning rush hour")
    assert peak_component(monday_evening, tz, 0.20, 0.25) == (0.25, "evening rush hour")
    assert peak_component(monday_midday, tz, 0.20, 0.25) == (0.0, None)
    assert peak_component(saturday_evening, tz, 0.20, 0.25) == (0.0, None)


def test_fare_rounding_and_multiplier():
    assert round_fare(85) == 90
    assert round_fare(96) == 100
    assert apply_multiplier(80, 120, 1.2) == (100, 140)
    assert apply_multiplier(80, 120, 1.0) == (80, 120)
    assert apply_multiplier(80, 120, 2.5) == (200, 300)
