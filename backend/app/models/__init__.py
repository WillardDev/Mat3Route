"""SQLAlchemy models.

Two model sets coexist during the merge:

* :mod:`app.models.legacy` — the synchronous weather/surge/accident/notification
  stack exposed by the API routers. These are re-exported here so existing
  ``from ..models import ...`` imports keep working.
* :mod:`app.models.orm` / :mod:`app.models.schemas` — the asynchronous
  route/SMS stack, imported explicitly as ``app.models.orm``.
"""

from .community import CommuterEvent, CommuterVote, RouteSubscription
from .legacy import (
    AccidentReport,
    AppUser,
    FareQuote,
    Notification,
    NotificationDevice,
    Route,
    RouteLine,
    Sacco,
    SurgeEvent,
    WeatherSnapshot,
)

__all__ = [
    "AccidentReport",
    "AppUser",
    "CommuterEvent",
    "CommuterVote",
    "FareQuote",
    "Notification",
    "NotificationDevice",
    "Route",
    "RouteLine",
    "RouteSubscription",
    "Sacco",
    "SurgeEvent",
    "WeatherSnapshot",
]
