"""Re-route proxy schemas — Mobile → Gateway → Layer 4.

The mobile client sends a lightweight payload; the gateway enriches it
with POI data from Redis cache (or the original itinerary) before
forwarding to Layer 4's /re-route endpoint.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class MobileReRouteRequest(BaseModel):
    """Request from mobile client for mid-day re-routing.

    The mobile sends its current GPS position, time, and the list of
    remaining POI IDs.  The full POI data + hotel + constraints come
    from the ``original_itinerary`` attached by the mobile.
    """
    current_lat: float = Field(..., description="Traveler current GPS latitude")
    current_lon: float = Field(..., description="Traveler current GPS longitude")
    current_time_min: int = Field(..., description="Current time in minutes from midnight")
    remaining_poi_ids: List[str] = Field(..., description="POI IDs still to visit today")
    excluded_poi_ids: Optional[List[str]] = Field(None, description="POI IDs to skip")
    day_index: int = Field(..., description="Current day index in the itinerary")
    # Full original itinerary from mobile — Gateway extracts POIs/hotel/constraints
    original_itinerary: dict = Field(..., description="Full TravelItinerary from the original plan")


class ReRouteResponse(BaseModel):
    """Response wrapper for re-route result."""
    status: str = Field("success")
    day: Optional[dict] = Field(None, description="Updated TravelItineraryDay")
    message: Optional[str] = None
