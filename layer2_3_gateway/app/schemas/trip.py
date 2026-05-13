"""Pydantic schemas bridging Layer 2 (LLM) → Layer 3 (DB) → Layer 4 (Solver)."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from geojson_pydantic import Point
from pydantic import BaseModel, Field, ConfigDict


# === Layer 2 Output: LLM extracts this from user text ===

class TimeWindowSpec(BaseModel):
    start_min: int = Field(480, description="Start time in minutes from midnight")
    end_min: int = Field(1260, description="End time in minutes from midnight")


class LLMDataContract(BaseModel):
    """JSON contract produced by Layer 2 (LLM intent extraction)."""
    budget_max: Optional[float] = Field(None, description="Max budget in VND")
    radius_km: float = Field(10.0, description="Search radius from hotel in km")
    num_days: int = Field(1, description="Number of travel days")
    time_window: Optional[TimeWindowSpec] = None
    tags: List[str] = Field(default_factory=list, description="Preference tags")
    locked_pois: List[str] = Field(default_factory=list, description="Must-visit POI names")
    weather_preference: Optional[str] = Field(None, description="indoor/outdoor/any")
    hotel_lat: float = Field(..., description="Hotel latitude")
    hotel_lon: float = Field(..., description="Hotel longitude")
    hotel_name: str = Field("Hotel", description="Hotel display name")


# === Layer 3 Output: POI returned from spatial filter ===

class POIResponse(BaseModel):
    """Single POI result from Layer 3 spatial filter."""
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    category: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    visit_duration_min: int = 60
    price: float = 0.0
    entrance_fee: float = 0.0
    open_time: int = 480
    close_time: int = 1260
    priority_score: float = 0.5
    tags: Optional[List[str]] = None
    is_locked: bool = False


# === Orchestrator Output: Assembled for Layer 4 ===

class TripPlanRequest(BaseModel):
    """User-facing request: just send text + hotel info."""
    user_prompt: str = Field(..., description="Natural language travel request")
    hotel_lat: float = Field(..., description="Hotel latitude")
    hotel_lon: float = Field(..., description="Hotel longitude")
    hotel_name: str = Field("Hotel", description="Hotel name")
    num_days: int = Field(1, description="Number of travel days")


class TripPlanResponse(BaseModel):
    """Response from orchestrator (wraps Layer 4 output)."""
    status: str = "success"
    llm_contract: Optional[LLMDataContract] = None
    pois_found: int = 0
    locked_pois: int = 0
    layer4_result: Optional[dict] = None
    message: Optional[str] = None
