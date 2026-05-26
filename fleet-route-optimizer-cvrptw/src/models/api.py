"""API request/response models."""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from .domain import POI, Hotel, DayPlan, Location, TravelConstraints


class SolverConfig(BaseModel):
    """Solver configuration parameters."""
    time_limit: int = Field(120, description="Time limit in seconds", ge=1, le=3600)
    solver: str = Field("ortools", description="Solver type: 'ortools'")
    distance_weight: float = Field(1.0, description="Weight for distance minimization")


class TravelPlanRequest(BaseModel):
    """Request to create an optimized travel itinerary."""
    pois: List[POI] = Field(..., description="List of candidate POIs (max 50, pre-filtered by Layer 3)")
    hotels: List[Hotel] = Field(..., description="Hotels for each day/segment of the trip")
    constraints: TravelConstraints = Field(..., description="Hard constraints from user")
    day_plans: Optional[List[DayPlan]] = Field(None, description="Custom day plans (auto-generated if None)")
    solver_config: Optional[SolverConfig] = Field(None, description="Solver tuning parameters")
    metadata: Optional[Dict] = Field(None, description="Additional metadata from Layer 3")


class ReRouteRequest(BaseModel):
    """Request to re-route remaining POIs from current location (JIT).

    Used when a traveler needs to recalculate their route mid-day,
    e.g. due to traffic changes or schedule adjustments.
    """
    current_location: Location = Field(..., description="Traveler's current GPS position")
    current_time_min: int = Field(..., description="Current time in minutes from midnight")
    remaining_poi_ids: List[str] = Field(..., description="IDs of POIs still to visit")
    pois: List[POI] = Field(..., description="Full POI objects for the solver")
    hotel: Hotel = Field(..., description="Hotel (return point at end of day)")
    day: DayPlan = Field(..., description="Current day plan")
    constraints: TravelConstraints = Field(..., description="User constraints")
    excluded_poi_ids: Optional[List[str]] = Field(None, description="POI IDs to skip (e.g. due to traffic)")
