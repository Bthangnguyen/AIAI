"""LLM-Driven Post-Solver Itinerary Validation & Adjustment Layer."""

import openai
import instructor
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.config import settings as global_settings
from app.schemas.trip import LLMDataContract, POIResponse
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()


class ItineraryAdjustment(BaseModel):
    action: Literal["ADD", "REMOVE", "REORDER", "KEEP"] = Field(
        ...,
        description="ADD: thêm POI từ candidates, REMOVE: xóa POI khỏi lịch trình, REORDER: sắp xếp lại thứ tự, KEEP: giữ nguyên"
    )
    day_index: int = Field(
        ...,
        description="Index của ngày cần điều chỉnh (0-indexed)"
    )
    poi_id: Optional[str] = Field(
        None,
        description="UUID của POI cần thêm hoặc xóa. Để trống nếu là REORDER hoặc KEEP"
    )
    insert_index: Optional[int] = Field(
        None,
        description="Vị trí chèn POI mới (đối với ADD) (0-indexed)"
    )
    new_order_ids: Optional[List[str]] = Field(
        None,
        description="Danh sách UUID các điểm đỗ theo thứ tự mới (đối với REORDER)"
    )
    reason: str = Field(
        ...,
        description="Giải thích lý do điều chỉnh tại sao việc này giúp lịch trình hợp lý hơn"
    )


class ItineraryValidationResponse(BaseModel):
    is_reasonable: bool = Field(
        ...,
        description="Đánh giá tổng quan xem lịch trình hiện tại đã hợp lý chưa"
    )
    overall_analysis: str = Field(
        ...,
        description="Phân tích tổng quan về lịch trình, thứ tự di chuyển, tần suất lặp lại địa điểm"
    )
    adjustments: List[ItineraryAdjustment] = Field(
        default_factory=list,
        description="Danh sách các đề xuất điều chỉnh cần thực hiện"
    )


ITINERARY_VALIDATOR_SYSTEM_PROMPT = """You are a master travel optimizer and human coordinator. 
Your job is to analyze the proposed travel itinerary produced by a mathematical routing solver (OR-Tools) and adjust it to make it more human-reasonable, logical, and diverse.

The mathematical solver optimizes for short travel distances and high score density, but it doesn't understand human nuances like pacing limits, category repetition, and logical timing.

You MUST strictly enforce the following travel and human-pacing constraints:

1. STOPS PACING LIMITS (CRITICAL):
   Review the traveler's 'Pace' and profile. You MUST prune the number of daily stops to be strictly within these limits (excluding the starting/ending hotel):
   - 'chill' or 'family' (gentle/chill/gia đình/nhẹ nhàng) -> STRICTLY Max 4 stops per day. If a day has 5 or more stops, you MUST aggressively emit REMOVE actions for the lowest-priority, most exhausting, or redundant stops until there are exactly at most 4 stops remaining.
   - 'balanced' (standard pace) -> STRICTLY Max 5 stops per day. If a day has 6 or more stops, prune it down to at most 5 stops.
   - 'intense' (active pace) -> STRICTLY Max 6 stops per day. If a day has 7 or more stops, prune it down to at most 6 stops.
   This guarantees that NO itinerary day will ever exceed 6 stops, ensuring a comfortable and relaxed journey.

2. CATEGORY DIVERSITY, OPTIONAL LIMITS & ANTI-FATIGUE RULES:
   - Optional Categories Cap (CRITICAL): Under no circumstance should there be more than 1 Cafe stop, more than 1 Shopping stop, or more than 1 Art/Gallery stop on the same day. If any day has 2 or more cafes, or 2 or more shopping stops, or 2 or more art stops, you MUST immediately REMOVE the redundant ones.
   - Wellness Sites Ban: Any spa, massage, or wellness stop is completely forbidden. If any slip into the solver output, REMOVE them immediately.
   - Temple/Pagoda Fatigue: Max 2 religious sites (pagodas, temples, churches) per day. Never schedule them consecutively. If there are too many, REMOVE the redundant ones and ADD a relaxing nature park or cafe stop from the candidates.
   - No Back-to-Back Cafes/Bars: Never schedule consecutive cafe, coffee shop, or tea shop stops on the same day. Space them out.
   - No Consecutive Food/Meals: Do not schedule two food stops consecutively unless one is a small street-food snack and the other is a dinner.

3. LOGICAL TIME SEQUENCING:
   - Cafe/Tea Stops: Should be at logical times (e.g., morning 8:30-10:30, afternoon 14:30-16:30). Avoid scheduling a cafe stop late at night (e.g. after 20:30) or during standard lunch hours (12:00-13:30) unless it's a food-focused cafe.
   - Outdoor active sites (nature viewpoints, hiking, long walks): Avoid scheduling in the intense midday heat (11:30-14:30). Group indoor or shaded activities during these hours.
   - Late night stops: Avoid scheduling family-unfriendly places or regular attractions that close early late at night (e.g. after 21:00). Late night stops should only be night cruises, night markets, or bars.

You are given:
1. Traveler's Profile: Destination, budget, pace, interests (tags), etc.
2. Proposed Itinerary (stops planned per day, chronological).
3. Candidate POIs: Additional suitable POIs in the area that were NOT selected by the solver, with their tags, descriptions, priority scores, and categories.

Your goal:
Review the itinerary. If it already satisfies all the constraints, return `is_reasonable = True` and an empty list of adjustments.
If it violates any of the pacing or diversity rules (such as having more than 6 stops, or two cafes in a day, or 4 temples in a day), return `is_reasonable = False` and emit a structured list of adjustments (REMOVE, ADD, REORDER) to make it perfect.

Be extremely precise. Only make adjustments that genuinely improve the traveler's experience. Explain your reasoning in detail for each adjustment.
"""


class ItineraryValidatorService:
    """Validator layer that optimizes Layer 4 outputs with structured LLM completions."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if global_settings.LLM_PROVIDER == "openrouter":
                base_client = openai.AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=global_settings.OPENROUTER_API_KEY,
                )
            elif global_settings.LLM_PROVIDER == "shopaikey":
                base_client = openai.AsyncOpenAI(
                    base_url="https://api.shopaikey.com/v1",
                    api_key=global_settings.OPENAI_API_KEY,
                )
            else:
                base_client = openai.AsyncOpenAI(api_key=global_settings.OPENAI_API_KEY)

            if global_settings.LLM_PROVIDER in ("shopaikey", "openrouter"):
                self._client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
            else:
                self._client = instructor.from_openai(base_client)
        return self._client

    async def validate_and_adjust(
        self,
        l4_result: dict,
        contract: LLMDataContract,
        all_pois: List[POIResponse],
    ) -> dict:
        """Call LLM validator to review the solver itinerary and apply adjustments."""
        if not l4_result or "days" not in l4_result:
            return l4_result

        # Identify Candidate POIs that were not selected or dropped
        selected_ids = set()
        for day in l4_result.get("days", []):
            for stop in day.get("stops", []):
                selected_ids.add(stop.get("poi_id"))

        # Filter out excluded/avoided POIs from candidates
        avoid_tags_set = set(t.lower() for t in (contract.avoid_tags or []))
        excluded_names = [n.strip().lower() for n in (contract.excluded_pois or [])]

        candidates = [
            p for p in all_pois
            if str(p.uuid) not in selected_ids
            and not any(t.lower() in avoid_tags_set for t in (p.tags or []))
            and not any(ex in (p.name or '').lower() for ex in excluded_names if ex)
        ]
        candidates_str = "\n".join([
            f"- [{p.category}] {p.name} (UUID: {p.uuid}) | tags: {p.tags} | score: {p.priority_score:.2f} | description: {p.description}"
            for p in candidates[:25]
        ])

        proposed_itinerary_str = ""
        for day_idx, day in enumerate(l4_result.get("days", [])):
            proposed_itinerary_str += f"\n--- Day {day_idx + 1} ---\n"
            for stop_idx, stop in enumerate(day.get("stops", [])):
                proposed_itinerary_str += (
                    f"  {stop_idx + 1}. {stop.get('poi_name')} (UUID: {stop.get('poi_id')}) | "
                    f"arrival: {stop.get('arrival_time_min')}m | departure: {stop.get('departure_time_min')}m | "
                    f"category: {stop.get('category')}\n"
                )

        # Build exclusion context for the validator
        avoid_str = ", ".join(contract.avoid_tags or [])
        excluded_str = ", ".join(contract.excluded_pois or [])
        exclusion_block = ""
        if avoid_str or excluded_str:
            exclusion_block = (
                f"\n=== USER EXCLUSIONS (CRITICAL - NEVER ADD THESE) ===\n"
                f"Avoid tags/categories: {avoid_str or 'none'}\n"
                f"Excluded POI names: {excluded_str or 'none'}\n"
                f"You MUST NEVER add any POI matching these exclusions.\n"
                f"You MUST REMOVE any existing stop that matches these exclusions.\n"
            )

        prompt = (
            f"=== TRAVELER PROFILE ===\n"
            f"Destination: {contract.destination}\n"
            f"Pace: {contract.preferred_pace}\n"
            f"Walking tolerance: {contract.walking_tolerance}\n"
            f"Interests/Tags: {contract.tags}\n"
            f"Budget: {contract.budget_max}\n"
            f"{exclusion_block}\n"
            f"=== PROPOSED SOLVER ITINERARY ===\n"
            f"{proposed_itinerary_str}\n\n"
            f"=== UNSELECTED CANDIDATE POIS ===\n"
            f"{candidates_str}\n"
        )

        try:
            response: ItineraryValidationResponse = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=ItineraryValidationResponse,
                messages=[
                    {"role": "system", "content": ITINERARY_VALIDATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4000,
                max_retries=2,
                timeout=60.0,
            )

            logger.info(
                f"Itinerary validation complete. Reasonable? {response.is_reasonable}. "
                f"Found {len(response.adjustments)} adjustments. Analysis: {response.overall_analysis}"
            )

            if response.adjustments:
                l4_result = self._apply_adjustments(l4_result, response.adjustments, all_pois)

        except Exception as e:
            logger.error(f"Failed to execute LLM itinerary validator: {e}", exc_info=True)
            # Failsafe: return unmodified solver result if LLM fails
            pass

        return l4_result

    def _apply_adjustments(self, l4_result: dict, adjustments: List[ItineraryAdjustment], all_pois: List[POIResponse]) -> dict:
        """Apply adjustments (ADD, REMOVE, REORDER) to the itinerary and recalculate timings."""
        poi_map = {str(p.uuid): p for p in all_pois}
        days = l4_result.get("days", [])

        for adj in adjustments:
            day_idx = adj.day_index
            if day_idx < 0 or day_idx >= len(days):
                continue
            day = days[day_idx]

            if adj.action == "REMOVE":
                if not adj.poi_id:
                    continue
                day["stops"] = [s for s in day.get("stops", []) if s.get("poi_id") != adj.poi_id]
                logger.info(f"Validator: Removed stop {adj.poi_id} from Day {day_idx}. Reason: {adj.reason}")

            elif adj.action == "ADD":
                if not adj.poi_id or adj.poi_id not in poi_map:
                    continue
                poi = poi_map[adj.poi_id]
                new_stop = {
                    "poi_id": str(poi.uuid),
                    "poi_name": poi.name,
                    "location": {
                        "latitude": poi.latitude,
                        "longitude": poi.longitude
                    },
                    "visit_duration_min": poi.visit_duration_min,
                    "entrance_fee": poi.entrance_fee,
                    "category": poi.category,
                    "description": poi.description
                }
                stops = day.get("stops", [])
                idx = adj.insert_index if adj.insert_index is not None else len(stops)
                idx = max(0, min(idx, len(stops)))
                stops.insert(idx, new_stop)
                day["stops"] = stops
                logger.info(f"Validator: Added stop {poi.name} to Day {day_idx} at index {idx}. Reason: {adj.reason}")

            elif adj.action == "REORDER":
                if not adj.new_order_ids:
                    continue
                stops = day.get("stops", [])
                stop_map = {s["poi_id"]: s for s in stops if "poi_id" in s}
                new_stops = []
                for pid in adj.new_order_ids:
                    if pid in stop_map:
                        new_stops.append(stop_map[pid])
                # Add any missing stops at the end to be safe
                for s in stops:
                    if s["poi_id"] not in adj.new_order_ids:
                        new_stops.append(s)
                day["stops"] = new_stops
                logger.info(f"Validator: Reordered stops for Day {day_idx}. Reason: {adj.reason}")

            # Recalculate day timings after any change to that day
            self._recalculate_day_timings(day)

        return l4_result

    def _recalculate_day_timings(self, day: dict):
        """Sequential re-interpolation of stop arrival/departure times."""
        stops = day.get("stops", [])
        if not stops:
            day["total_visit_min"] = 0
            day["num_pois"] = 0
            return

        # Default start time is 08:00 (480 min) or from day_plan
        current_time = day.get("start_time_min", 480)
        total_visit = 0
        total_fee = 0.0

        for stop in stops:
            travel_time = 15  # standard average fallback travel time in minutes
            arrival = current_time + travel_time
            duration = stop.get("visit_duration_min", 60)

            stop["arrival_time_min"] = arrival
            stop["departure_time_min"] = arrival + duration
            stop["travel_time_from_prev_min"] = travel_time

            current_time = stop["departure_time_min"]
            total_visit += duration
            total_fee += stop.get("entrance_fee", 0.0)

        day["total_visit_min"] = total_visit
        day["total_entrance_fee"] = total_fee
        day["num_pois"] = len(stops)
