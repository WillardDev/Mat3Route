from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class WeatherLike(Protocol):
    condition_main: str
    description: str
    temperature_c: float
    wind_speed_mps: float | None


@dataclass(frozen=True, slots=True)
class WeatherAssessment:
    component: float
    severity: int
    label: str

    @property
    def is_severe(self) -> bool:
        return self.severity >= 3


@dataclass(frozen=True, slots=True)
class WeatherChange:
    significant: bool
    direction: str
    reason: str | None
    label: str


def assess(weather: WeatherLike, max_component: float = 0.40) -> WeatherAssessment:
    """Convert current conditions into a fare component and severity rank."""
    main = (weather.condition_main or "").lower()
    description = (weather.description or "").lower()
    component = 0.0
    severity = 0
    label = "clear"

    if main in {"thunderstorm", "tornado", "squall"}:
        component, severity, label = 0.35, 5, "thunderstorm"
    elif main == "rain":
        if any(word in description for word in ("heavy", "extreme", "torrential")):
            component, severity, label = 0.30, 4, "heavy rain"
        elif "light" in description:
            component, severity, label = 0.10, 2, "light rain"
        else:
            component, severity, label = 0.20, 3, "rain"
    elif main == "drizzle":
        component, severity, label = 0.08, 1, "drizzle"
    elif main == "snow":
        component, severity, label = 0.30, 4, "snow"
    elif main in {"mist", "fog", "haze", "smoke", "dust", "sand", "ash"}:
        component, severity, label = 0.05, 1, main

    if weather.temperature_c >= 35:
        heat_component = min(0.15 + (weather.temperature_c - 35) * 0.02, 0.25)
        if heat_component > component:
            component = heat_component
            label = "extreme heat"
        severity = max(severity, 2)
    elif weather.temperature_c >= 32 and component == 0:
        component, severity, label = 0.05, 1, "high heat"

    wind = weather.wind_speed_mps or 0.0
    if wind >= 12:
        component += 0.10 if wind < 17 else 0.15
        severity = max(severity, 2)
        label = f"{label} and high wind" if label != "clear" else "high wind"

    return WeatherAssessment(
        component=round(min(component, max_component), 2),
        severity=severity,
        label=label,
    )


def detect_change(
    current: WeatherLike,
    previous: WeatherLike | None,
    max_component: float = 0.40,
) -> WeatherChange:
    """Detect a meaningful change between two weather observations."""
    current_assessment = assess(current, max_component)

    if previous is None:
        if current_assessment.is_severe:
            return WeatherChange(
                significant=True,
                direction="worsened",
                reason=f"{current_assessment.label.capitalize()} detected",
                label=current_assessment.label,
            )
        return WeatherChange(False, "none", None, current_assessment.label)

    previous_assessment = assess(previous, max_component)
    component_delta = round(current_assessment.component - previous_assessment.component, 2)

    if current_assessment.is_severe and not previous_assessment.is_severe:
        return WeatherChange(
            significant=True,
            direction="worsened",
            reason=(
                f"{current_assessment.label.capitalize()} started after "
                f"{previous_assessment.label}"
            ),
            label=current_assessment.label,
        )

    if current_assessment.severity > previous_assessment.severity and component_delta >= 0.05:
        return WeatherChange(
            significant=True,
            direction="worsened",
            reason=(
                f"Conditions worsened from {previous_assessment.label} to "
                f"{current_assessment.label}"
            ),
            label=current_assessment.label,
        )

    if previous_assessment.is_severe and not current_assessment.is_severe:
        return WeatherChange(
            significant=True,
            direction="improved",
            reason=(
                f"Weather easing from {previous_assessment.label} to "
                f"{current_assessment.label}"
            ),
            label=current_assessment.label,
        )

    if component_delta >= 0.10:
        return WeatherChange(
            significant=True,
            direction="worsened",
            reason=(
                f"Weather risk increased from {previous_assessment.label} to "
                f"{current_assessment.label}"
            ),
            label=current_assessment.label,
        )

    if component_delta <= -0.10:
        return WeatherChange(
            significant=True,
            direction="improved",
            reason=(
                f"Weather risk eased from {previous_assessment.label} to "
                f"{current_assessment.label}"
            ),
            label=current_assessment.label,
        )

    return WeatherChange(False, "none", None, current_assessment.label)


def weather_component(weather: WeatherLike, max_component: float = 0.40) -> float:
    return assess(weather, max_component).component
