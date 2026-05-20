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
    destination: Optional[str] = Field(None, description="Destination city name")
    budget_max: Optional[float] = Field(None, description="Max budget in VND")
    radius_km: float = Field(10.0, description="Search radius from hotel in km")
    num_days: int = Field(1, description="Number of travel days")
    time_window: Optional[TimeWindowSpec] = None
    tags: List[str] = Field(default_factory=list, description="Preference tags")
    locked_pois: List[str] = Field(default_factory=list, description="Must-visit POI names")
    weather_preference: Optional[str] = Field(None, description="indoor/outdoor/any")
    hotel_lat: Optional[float] = Field(None, description="Hotel latitude")
    hotel_lon: Optional[float] = Field(None, description="Hotel longitude")
    hotel_name: Optional[str] = Field("Hotel", description="Hotel display name")


class ChatProcessResponse(BaseModel):
    """Output of /chat_process containing status, AI reply, and updated contract."""
    status: str = Field(..., description="'ready' or 'clarifying'")
    reply: str = Field(..., description="Conversational Vietnamese response or follow-up question")
    updated_contract: LLMDataContract


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
    """User-facing request: text, optional hotel info. Backend auto-picks hotel if missing."""
    user_prompt: str = Field(..., description="Natural language travel request")
    num_days: Optional[int] = Field(None, description="Number of travel days")
    budget: Optional[float] = Field(None, description="Target budget (VND)")
    destination: Optional[str] = Field("Huế", description="Destination city")
    preferences: Optional[List[str]] = Field(None, description="Additional preference tags")
    hotel_lat: Optional[float] = Field(None, description="Hotel latitude")
    hotel_lon: Optional[float] = Field(None, description="Hotel longitude")
    hotel_name: Optional[str] = Field(None, description="Hotel name")


class TripPlanResponse(BaseModel):
    """Response from orchestrator (wraps Layer 4 output)."""
    status: str = "success"
    llm_contract: Optional[LLMDataContract] = None
    pois: Optional[List[POIResponse]] = None
    locked_pois: int = 0
    layer4_result: Optional[dict] = None
    message: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatProcessRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    current_contract: LLMDataContract
