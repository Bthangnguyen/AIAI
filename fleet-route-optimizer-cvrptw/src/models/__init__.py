"""Data models for travel route optimizer."""

from .domain import (
    Location,
    TimeWindow,
    ProblemData,
    # New travel models
    POI,
    Hotel,
    DayPlan,
    TransportMode,
    TravelConstraints,
    # Travel response models
    TravelItineraryStop,
    TravelItineraryDay,
    TravelItinerary,
)
from .api import (
    SolverConfig,
    TravelPlanRequest,
    ReRouteRequest,
)
from .errors import (
    ErrorCode,
    SolverException,
)

__all__ = [
    # Shared primitives
    "Location",
    "TimeWindow",
    "ProblemData",
    # Travel models
    "POI",
    "Hotel",
    "DayPlan",
    "TransportMode",
    "TravelConstraints",
    # Travel response
    "TravelItineraryStop",
    "TravelItineraryDay",
    "TravelItinerary",
    # API models
    "SolverConfig",
    "TravelPlanRequest",
    "ReRouteRequest",
    # Errors
    "ErrorCode",
    "SolverException",
]

