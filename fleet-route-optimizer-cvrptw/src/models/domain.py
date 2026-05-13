"""Domain models for CVRPTW problem representation and Travel Routing."""

from typing import List, Dict, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Geographic location with coordinates."""
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")

    def as_tuple(self) -> Tuple[float, float]:
        """Return location as (lat, lon) tuple."""
        return (self.latitude, self.longitude)


class TimeWindow(BaseModel):
    """Time window constraint for a location."""
    start_min: int = Field(..., description="Start time in minutes from midnight")
    end_min: int = Field(..., description="End time in minutes from midnight")
    start_hhmm: Optional[str] = Field(None, description="Start time in HH:MM format")
    end_hhmm: Optional[str] = Field(None, description="End time in HH:MM format")


class ProblemData(BaseModel):
    """Complete CVRPTW problem data used internally by the OR-Tools solver wrapper."""
    locations: List[Tuple[float, float]] = Field(..., description="List of (lat, lon) tuples")
    demands: List[int] = Field(..., description="Demand at each location")
    time_windows: List[Tuple[int, int]] = Field(..., description="Time window (start, end) for each location")
    vehicle_capacities: List[int] = Field(..., description="Capacity of each vehicle")
    num_vehicles: int = Field(..., description="Number of available vehicles")
    depot: int = Field(0, description="Index of depot location")
    service_time: int = Field(15, description="Service time in minutes")
    coord_type: str = Field("latlon", description="Coordinate type: 'latlon' or 'euclidean'")
    distance_matrix: Optional[List[List[float]]] = Field(None, description="Precomputed distance matrix")
    time_matrix: Optional[List[List[int]]] = Field(None, description="Precomputed time matrix (scaled by 100)")
    is_locked_list: Optional[List[bool]] = Field(None, description="Whether each location is locked (cannot be dropped)")


# === Travel Domain Models ===

class POI(BaseModel):
    """Point of Interest for travel itinerary."""
    id: str = Field(..., description="Unique POI identifier")
    name: str = Field(..., description="POI display name")
    category: str = Field(..., description="POI category (museum, market, park, temple, etc.)")
    location: Location = Field(..., description="POI coordinates")
    visit_duration_min: int = Field(..., description="Recommended visit duration in minutes")
    time_window: Optional[TimeWindow] = Field(None, description="Opening hours as time window")
    entrance_fee: float = Field(0.0, description="Entrance fee in VND")
    priority_score: float = Field(0.5, description="Priority score from Layer 3 (0.0-1.0)")
    tags: Optional[List[str]] = Field(None, description="Tags: outdoor, indoor, family, etc.")
    description: Optional[str] = Field(None, description="Short description")
    is_locked: bool = Field(False, description="Must visit by all means (no disjunction penalty)")


class Hotel(BaseModel):
    """Hotel / accommodation — acts as depot for each day."""
    id: str = Field(..., description="Unique hotel identifier")
    name: str = Field(..., description="Hotel display name")
    location: Location = Field(..., description="Hotel coordinates")
    check_in_time: int = Field(840, description="Check-in time in minutes from midnight (default 14:00)")
    check_out_time: int = Field(720, description="Check-out time in minutes from midnight (default 12:00)")
    assigned_days: Optional[List[int]] = Field(None, description="Which day indices use this hotel as depot")


class DayPlan(BaseModel):
    """A single day's plan — maps to a 'vehicle' in CVRPTW formulation.

    Each day has a time budget (max_daily_minutes) which acts as 'capacity',
    and each POI's visit_duration_min acts as 'demand'.
    """
    day_index: int = Field(..., description="0-based day index in the trip")
    date: str = Field(..., description="Date string YYYY-MM-DD")
    hotel_id: Optional[str] = Field(None, description="Hotel ID for this day's start/end point")
    start_time_min: int = Field(480, description="Day start time (default 08:00)")
    end_time_min: int = Field(1260, description="Day end time (default 21:00)")
    max_daily_minutes: int = Field(600, description="Max active minutes per day (default 10h)")
    max_pois: int = Field(10, description="Max number of POIs per day")


class TransportMode(str, Enum):
    """Supported transport modes."""
    WALKING = "walking"
    TAXI = "taxi"
    BUS = "bus"


class TravelConstraints(BaseModel):
    """Hard constraints for travel planning from the user."""
    num_days: int = Field(..., description="Number of travel days")
    budget_total: Optional[float] = Field(None, description="Total budget in VND (hard constraint)")
    transport_modes: List[TransportMode] = Field(
        default=[TransportMode.WALKING, TransportMode.TAXI, TransportMode.BUS],
        description="Allowed transport modes"
    )
    meal_break_enabled: bool = Field(False, description="Auto-insert meal breaks")
    meal_break_duration_min: int = Field(60, description="Meal break duration in minutes")
    meal_break_window: Optional[TimeWindow] = Field(
        None, description="Preferred meal time window (e.g. 11:30-13:30)"
    )


class TravelItineraryStop(BaseModel):
    """A single stop in a day's itinerary."""
    poi_id: str = Field(..., description="POI identifier")
    poi_name: str = Field(..., description="POI display name")
    location: Location = Field(..., description="Stop coordinates")
    arrival_time_min: int = Field(..., description="Arrival time (minutes from midnight)")
    departure_time_min: int = Field(..., description="Departure time (minutes from midnight)")
    visit_duration_min: int = Field(..., description="Time spent at this POI")
    travel_time_from_prev_min: int = Field(0, description="Travel time from previous stop")
    entrance_fee: float = Field(0.0, description="Entrance fee paid at this POI")


class TravelItineraryDay(BaseModel):
    """One day's optimized itinerary."""
    day_index: int = Field(..., description="0-based day index")
    date: str = Field(..., description="Date YYYY-MM-DD")
    hotel_name: str = Field(..., description="Hotel name for this day")
    hotel_location: Location = Field(..., description="Hotel coordinates (start/end)")
    stops: List[TravelItineraryStop] = Field(..., description="Ordered POI stops")
    total_travel_min: int = Field(..., description="Total travel time in minutes")
    total_visit_min: int = Field(..., description="Total visit time in minutes")
    total_distance_km: float = Field(..., description="Total distance traveled")
    total_entrance_fee: float = Field(0.0, description="Total entrance fees for this day")
    num_pois: int = Field(..., description="Number of POIs visited")


class TravelItinerary(BaseModel):
    """Complete multi-day travel itinerary — final response."""
    status: str = Field("success", description="success or error")
    num_days: int = Field(..., description="Number of days")
    days: List[TravelItineraryDay] = Field(..., description="Per-day itineraries")
    total_pois_visited: int = Field(..., description="Total POIs across all days")
    total_pois_dropped: int = Field(0, description="POIs not included")
    total_entrance_fee: float = Field(0.0, description="Total entrance fees")
    total_travel_min: int = Field(0, description="Total travel time")
    total_distance_km: float = Field(0.0, description="Total distance")
    budget_total: Optional[float] = Field(None, description="Budget limit")
    budget_used: float = Field(0.0, description="Budget consumed")
    dropped_pois: Optional[List[Dict]] = Field(None, description="POIs not visited")
    solver: Optional[str] = Field(None, description="Solver used")
    message: Optional[str] = Field(None, description="Error/info message")
