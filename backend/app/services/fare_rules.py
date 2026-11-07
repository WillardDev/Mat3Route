from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

ACCIDENT_WEIGHTS = {"low": 0.10, "medium": 0.20, "high": 0.35}


def peak_component(
    now: datetime,
    timezone: str,
    morning_component: float,
    evening_component: float,
) -> tuple[float, str | None]:
    """Return the rush-hour component and a human-readable label."""
    local = now.astimezone(ZoneInfo(timezone))
    if local.weekday() >= 5:  # Saturday/Sunday
        return 0.0, None

    minutes = local.hour * 60 + local.minute
    if 6 * 60 + 30 <= minutes < 9 * 60 + 30:
        return morning_component, "morning rush hour"
    if 17 * 60 <= minutes < 20 * 60:
        return evening_component, "evening rush hour"
    return 0.0, None


def accident_component(reports: list[object], max_component: float) -> float:
    total = sum(ACCIDENT_WEIGHTS.get(getattr(report, "severity", "medium"), 0.20) for report in reports)
    return round(min(total, max_component), 2)


def round_fare(value: float) -> int:
    """Kenyan matatu fares are normally quoted in multiples of KSh 10."""
    rounded = (Decimal(str(value)) / Decimal(10)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(rounded * 10)


def apply_multiplier(base_min: int, base_max: int, multiplier: float) -> tuple[int, int]:
    fare_min = max(round_fare(base_min * multiplier), base_min)
    fare_max = max(round_fare(base_max * multiplier), fare_min)
    return fare_min, fare_max
