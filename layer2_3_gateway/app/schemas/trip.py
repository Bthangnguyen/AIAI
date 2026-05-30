"""Pydantic schemas bridging Layer 2 (LLM) → Layer 3 (DB) → Layer 4 (Solver)."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from geojson_pydantic import Point
from pydantic import BaseModel, Field, ConfigDict, field_validator
import json


# === Layer 2 Output: LLM extracts this from user text ===


class TimeWindowSpec(BaseModel):
    start_min: int = Field(480, description="Start time in minutes from midnight")
    end_min: int = Field(1260, description="End time in minutes from midnight")


# === Layer 2 NEW: Structured LLM Intent Extraction Output ===


class ExtractionStatus(BaseModel):
    """Tracks whether enough info exists to generate an itinerary."""
    is_generate_ready: bool = False
    missing_required_fields: Optional[List[str]] = Field(default_factory=list)
    ambiguous_fields: Optional[List[str]] = Field(default_factory=list)
    needs_follow_up: bool = False
    follow_up_questions: Optional[List[str]] = Field(default_factory=list)
    assistant_reply: str = Field(
        "",
        description="Vietnamese conversational reply to send to user. "
                    "If needs_follow_up, this should be a natural question. "
                    "If is_generate_ready, this should be a confirmation summary asking user to confirm."
    )


class TripCore(BaseModel):
    """Core trip parameters extracted from user text."""
    destination: Optional[str] = None
    destination_raw: Optional[str] = None
    date_range: Optional[Dict[str, Optional[str]]] = Field(
        default_factory=lambda: {"start_date": None, "end_date": None}
    )
    duration_days: Optional[int] = None
    start_time_preference: Optional[str] = None
    end_time_preference: Optional[str] = None
    number_of_people: Optional[int] = None
    traveler_group_type: Optional[str] = None


class BudgetInfo(BaseModel):
    """Budget information extracted from user text."""
    amount: Optional[float] = None
    currency: str = "VND"
    budget_level: Optional[str] = Field(None, description="low/medium/high/unlimited")
    budget_scope: Optional[str] = Field(None, description="per_day/total_trip/per_person")


class UserPreferences(BaseModel):
    """User preferences for travel style, food, activities."""
    travel_style: Optional[List[str]] = Field(default_factory=list)
    pace: Optional[str] = Field(None, description="slow/moderate/fast")
    interest_tags: Optional[List[str]] = Field(default_factory=list)
    food_preferences: Optional[List[str]] = Field(default_factory=list)
    activity_preferences: Optional[List[str]] = Field(default_factory=list)
    transport_preferences: Optional[List[str]] = Field(default_factory=list)
    accommodation_preferences: Optional[List[str]] = Field(default_factory=list)
    avoid_tags: Optional[List[str]] = Field(default_factory=list)


class POIConstraints(BaseModel):
    """POI inclusion/exclusion constraints."""
    locked_pois: Optional[List[str]] = Field(default_factory=list, description="Must-visit POIs")
    mentioned_pois: Optional[List[str]] = Field(default_factory=list, description="POIs mentioned but not required")
    excluded_pois: Optional[List[str]] = Field(default_factory=list)
    excluded_categories: Optional[List[str]] = Field(default_factory=list)
    must_include_categories: Optional[List[str]] = Field(default_factory=list)


class RouteConstraints(BaseModel):
    """Route-level constraints (start/end location, distance limits)."""
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    current_location: Optional[str] = None
    max_travel_time_minutes: Optional[int] = None
    max_distance_km: Optional[float] = None
    allow_backtracking: Optional[bool] = None


class TimeConstraints(BaseModel):
    """Time-related constraints (meal times, fixed windows)."""
    fixed_time_windows: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    meal_time_preferences: Optional[List[str]] = Field(default_factory=list)
    rest_time_preferences: Optional[List[str]] = Field(default_factory=list)
    opening_hours_required: bool = True


class OperationItem(BaseModel):
    """Single atomic operation in a multi-intent edit request."""
    type: str = Field(..., description="add_place|remove_place|replace_place|swap_places|move_place|change_time|change_duration|change_distribution|change_budget|change_pace|add_preference|avoid_preference|rebuild_requested")
    target: Optional[str] = Field(None, description="Target POI name or category")
    target_day: Optional[int] = Field(None, description="Target day number")
    target_count: Optional[int] = Field(None, description="Number of POIs requested for add_place")
    query: Optional[str] = Field(None, description="Search query for add_place")
    amount: Optional[float] = Field(None, description="Budget amount for change_budget")
    value: Optional[str] = Field(None, description="New value for pace/time changes")
    target_category: Optional[str] = Field(None, description="Macro category such as food/cafe/culture/nightlife")
    target_micro_tags: Optional[List[str]] = Field(default_factory=list, description="Fine-grained tags such as bun_bo, che, cafe_muoi")
    time_window: Optional[Dict[str, int]] = Field(None, description="Preferred time window in minutes")
    target_time_min: Optional[int] = Field(None, description="Exact preferred arrival/start minute")
    position: Optional[str] = Field(None, description="before|after|first|last|best_gap")
    relative_to: Optional[str] = Field(None, description="Existing stop used as anchor for insert/move")
    resolution_strategy: Optional[str] = Field(None, description="current_itinerary_match|name_search|vector_search_then_suggest")


class UserOperation(BaseModel):
    """Edit/modification operation when user is modifying an existing itinerary."""
    target_day: Optional[int] = None
    target_poi: Optional[str] = None
    operation: Optional[str] = None
    operation_raw_text: Optional[str] = None
    operations: Optional[List[OperationItem]] = Field(default_factory=list, description="Multi-intent: list of atomic operations")


class NormalizationInfo(BaseModel):
    """LLM's normalized representation of the user query."""
    normalized_query: Optional[str] = None
    search_keywords: Optional[List[str]] = Field(default_factory=list)
    semantic_tags: Optional[List[str]] = Field(default_factory=list)
    raw_entities: Optional[List[str]] = Field(default_factory=list)


class ConfidenceScores(BaseModel):
    """Per-field confidence scores from LLM extraction."""
    overall: float = 0.0
    destination: float = 0.0
    duration: float = 0.0
    budget: float = 0.0
    preferences: float = 0.0
    operation: float = 0.0


class SafetyAndScope(BaseModel):
    """Safety and scope classification."""
    is_travel_related: bool = True
    contains_sensitive_request: bool = False
    unsupported_reason: Optional[str] = None


class LLMIntentExtraction(BaseModel):
    """Structured output from LLM Intent Extractor (new schema).

    This model captures the full structured extraction from the LLM,
    then gets converted to LLMDataContract via adapter for downstream compatibility.
    """
    intent_type: str = Field("create_itinerary", description="create_itinerary|modify_itinerary|add_place|remove_place|reroute|ask_information|compare_options|save_or_share|smalltalk|unsupported")
    language: str = Field("vi", description="vi|en|mixed|unknown")
    extraction_status: Optional[ExtractionStatus] = Field(default_factory=ExtractionStatus)
    trip_core: Optional[TripCore] = Field(default_factory=TripCore)
    budget: Optional[BudgetInfo] = Field(default_factory=BudgetInfo)
    preferences: Optional[UserPreferences] = Field(default_factory=UserPreferences)
    poi_constraints: Optional[POIConstraints] = Field(default_factory=POIConstraints)
    route_constraints: Optional[RouteConstraints] = Field(default_factory=RouteConstraints)
    time_constraints: Optional[TimeConstraints] = Field(default_factory=TimeConstraints)
    user_operation: Optional[UserOperation] = Field(default_factory=UserOperation)
    normalization: Optional[NormalizationInfo] = Field(default_factory=NormalizationInfo)
    confidence: Optional[ConfidenceScores] = Field(default_factory=ConfidenceScores)
    safety_and_scope: Optional[SafetyAndScope] = Field(default_factory=SafetyAndScope)

    # === Dynamic Distribution & Scope ===
    target_category_distribution: Optional[Dict[str, float]] = Field(
        None,
        description="Phân bổ % cho 9 category. Keys: food, cafe, culture, nature, "
                    "nightlife, shopping, art, wellness, adventure. Tổng = 1.0. "
                    "VD food tour: {food: 0.60, cafe: 0.20, culture: 0.10, nature: 0.10}"
    )
    estimated_pois: Optional[int] = Field(
        None, description="Predicted number of POIs user wants (2-3 cho buổi tối, 8-12 cho cả ngày)"
    )
    strict_poi_count: bool = Field(
        False, description="True when user explicitly requested an exact/near-exact number of POIs"
    )
    trip_duration_hours: Optional[float] = Field(
        None, description="Estimated active hours (VD: 5.0 cho buổi tối)"
    )



class LLMDataContract(BaseModel):
    """JSON contract produced by Layer 2 (LLM intent extraction)."""
    destination: Optional[str] = Field(None, description="Destination city name")
    budget_max: Optional[float] = Field(None, description="Max budget in VND")
    budget_is_unlimited: bool = Field(False, description="True when the user explicitly accepts unlimited/open budget")
    radius_km: float = Field(10.0, description="Search radius from hotel in km")
    num_days: int = Field(1, description="Number of travel days")
    time_window: Optional[TimeWindowSpec] = None
    tags: List[str] = Field(default_factory=list, description="Preference tags")
    locked_pois: List[str] = Field(default_factory=list, description="Must-visit POI names")
    excluded_pois: List[str] = Field(default_factory=list, description="POI names the user explicitly wants to avoid")
    weather_preference: Optional[str] = Field(None, description="indoor/outdoor/any")
    hotel_lat: Optional[float] = Field(None, description="Hotel latitude")
    hotel_lon: Optional[float] = Field(None, description="Hotel longitude")
    hotel_name: Optional[str] = Field("Hotel", description="Hotel display name")
    hotel_confirmed: bool = Field(False, description="True when hotel info or default hotel choice is confirmed")
    default_hotel_ok: bool = Field(False, description="True when user agrees to use the default Hue hotel")
    transport_modes: List[str] = Field(default_factory=list, description="Preferred transport modes")
    group_type: Optional[str] = Field(None, description="solo/couple/family/friends/business")
    group_size: Optional[int] = Field(None, description="Number of travelers")
    confirmed_fields: List[str] = Field(default_factory=list, description="Fields explicitly collected or confirmed")
    last_question_field: Optional[str] = Field(None, description="Field asked in the latest follow-up question")
    confirmation_pending: bool = Field(False, description="True after the assistant summarizes and waits for confirmation")
    ready_to_plan: bool = Field(False, description="True only after user confirms the complete contract")

    # === NEW: Scheduling Hints ===
    estimated_pois: Optional[int] = Field(
        None, description="Predicted number of POIs user wants (2-3 cho buổi tối, 8-12 cho cả ngày)"
    )
    strict_poi_count: bool = Field(
        False, description="True when user explicitly requested an exact/near-exact number of POIs"
    )
    time_slot: Optional[str] = Field(
        None, description="morning/afternoon/evening/full_day/multi_day"
    )
    trip_duration_hours: Optional[float] = Field(
        None, description="Estimated active hours (VD: 5.0 cho buổi tối)"
    )
    vibe: Optional[str] = Field(
        None, description="romantic/adventure/chill/cultural/foodie/family"
    )
    trip_type: Optional[str] = Field(
        None, description="sightseeing/food_tour/cafe_hopping/nightlife/mixed"
    )

    # === Preference weights ===
    preferred_pace: Optional[str] = Field(None, description="chill/balanced/intense")
    walking_tolerance: Optional[str] = Field(None, description="low/medium/high")
    food_preferences: List[str] = Field(default_factory=list, description="vegetarian, bun_bo, cafe_muoi, etc.")
    avoid_tags: List[str] = Field(default_factory=list, description="crowded, expensive, touristy")

    # === Target category distribution (LLM decides dynamically) ===
    target_category_distribution: Dict[str, float] = Field(
        default_factory=lambda: {
            "food": 0.35, "culture": 0.35, "nature": 0.20,
            "nightlife": 0.05, "adventure": 0.05
        },
        description="BẮT BUỘC. Phân bổ % cho 5 category chính. Keys: food, culture, nature, "
                    "nightlife, adventure. Tổng = 1.0. KHÔNG được null. "
                    "VD food tour: {food: 0.80, culture: 0.10, nature: 0.10}. "
                    "VD kết hợp: {food: 0.35, culture: 0.35, nature: 0.20, nightlife: 0.05, adventure: 0.05}"
    )
    distribution_description: Optional[str] = Field(
        None,
        description="1-2 câu mô tả phong cách chuyến đi bằng tiếng Việt để embed. "
                    "VD: 'Ẩm thực đường phố Huế: bún bò, bánh khoái, bánh bèo, chè Huế, cà phê muối'"
    )
    allow_cafe: bool = Field(False, description="True if coffee breaks are requested")
    allow_art: bool = Field(False, description="True if art/gallery stops are requested")
    allow_shopping: bool = Field(False, description="True if shopping stops are requested")
    distribution_locked: bool = Field(False, description="True if traveler explicitly confirmed highly biased distribution")


class EditIntent(BaseModel):
    """Structured intent for requests after an itinerary already exists."""
    action: str = Field(..., description="add_place|remove_place|replace_place|change_time|change_distribution|change_budget|change_pace|add_preference|avoid_preference|rebuild_requested|answer_question|info_reply")
    target: Optional[str] = None
    target_count: Optional[int] = Field(None, description="Number of POIs requested for add_place")
    constraints: Dict[str, Any] = Field(default_factory=dict)
    raw_message: str
    operations: List[OperationItem] = Field(default_factory=list, description="Multi-intent: decomposed atomic operations")


class ChatProcessResponse(BaseModel):
    """Output of /chat_process containing status, AI reply, and updated contract."""
    status: str = Field(..., description="'ready' or 'clarifying'")
    reply: str = Field(..., description="Conversational Vietnamese response or follow-up question")
    updated_contract: LLMDataContract
    phase: Optional[str] = Field(None, description="collecting/confirming/ready/editing")
    missing_fields: List[str] = Field(default_factory=list)
    next_question: Optional[str] = None
    requires_confirmation: bool = False
    edit_intent: Optional[EditIntent] = None
    pending_edit_plan: Optional[Dict[str, Any]] = Field(None, description="Preview edit plan waiting for user confirmation")
    updated_itinerary: Optional[Dict[str, Any]] = Field(None, description="The JIT-edited itinerary returned to the frontend if an edit was performed in-memory")

    @field_validator("updated_contract", "edit_intent", mode="before")
    @classmethod
    def parse_json_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                pass
        return v



# === Layer 3 Output: POI returned from spatial filter ===

class POIScoreBreakdown(BaseModel):
    """Per-POI utility breakdown — transparent scoring."""
    semantic_score: float = Field(0.5, description="pgvector cosine similarity to user intent")
    quality_score: float = Field(0.5, description="Rating + review count + popularity")
    distribution_boost: float = Field(0.5, description="Boost from LLM target_category_distribution")
    intent_tag_match: float = Field(0.5, description="Deterministic match between user intent tags and POI tags/name/category")
    localness_score: float = Field(0.5, description="Tính bản địa, không generic")
    novelty_score: float = Field(0.5, description="Khác biệt so với lịch trình bình thường")
    comfort_score: float = Field(0.5, description="Phù hợp pace/walking tolerance của user")
    budget_score: float = Field(0.5, description="Cost-value ratio so với budget user")
    distance_score: float = Field(0.5, description="Gần hotel/cluster hiện tại")
    diversity_gain: float = Field(0.0, description="Marginal diversity gain khi thêm POI này")


class POIResponse(BaseModel):
    """Single POI result from Layer 3 spatial filter."""
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    category: str
    category_group: Optional[str] = None
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
    score_breakdown: Optional[POIScoreBreakdown] = None
    utility_score: float = Field(0.5, description="Weighted sum of breakdown scores")


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
    contract: Optional[LLMDataContract] = Field(None, description="Confirmed Layer 2 contract; skips LLM extraction when present")


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


class AppContext(BaseModel):
    """UI context sent with chat messages for disambiguation."""
    screen: Optional[str] = Field(None, description="current_screen: home|itinerary_draft|poi_detail")
    selected_day: Optional[int] = Field(None, description="Currently selected day number")
    selected_poi_id: Optional[str] = Field(None, description="Currently selected POI UUID")
    selected_poi_name: Optional[str] = Field(None, description="Currently selected POI name")


class ChatProcessRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    current_contract: LLMDataContract
    has_draft: bool = Field(False, description="True when the user is editing an existing itinerary")
    app_context: Optional[AppContext] = Field(None, description="UI context for disambiguation")
    current_itinerary: Optional[Dict[str, Any]] = Field(None, description="The current itinerary JSON representation from the frontend to enable JIT editing")
    pending_edit_plan: Optional[Dict[str, Any]] = Field(None, description="Unapplied edit plan returned by a previous post-draft chat turn")
