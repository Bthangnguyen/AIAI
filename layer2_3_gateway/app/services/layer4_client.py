"""HTTP client for Layer 4 (OR-Tools Routing Engine)."""

import httpx
from typing import Optional, Dict, List
from app.config import settings
from app.schemas.trip import POIResponse, LLMDataContract
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()


from app.services.transport_modes import transport_modes_from_contract


class Layer4Client:
    """Assembles TravelPlanRequest and sends to Layer 4 API."""

    def __init__(self):
        self.base_url = settings.LAYER4_BASE_URL

    def _build_payload(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
    ) -> Dict:
        """Assemble TravelPlanRequest matching Layer 4 schema exactly."""
        # Build POI list matching Layer 4's POI model
        l4_pois = []
        for p in pois:
            l4_pois.append({
                "id": str(p.uuid),
                "name": p.name,
                "category": p.category,
                "location": {"latitude": p.latitude, "longitude": p.longitude},
                "visit_duration_min": p.visit_duration_min,
                "time_window": {
                    "start_min": p.open_time,
                    "end_min": p.close_time,
                },
                "entrance_fee": p.entrance_fee,
                "priority_score": p.utility_score,  # utility_score from Phase 0B scorer
                "tags": p.tags or [],
                "description": p.description,
                "is_locked": p.is_locked,
            })

        # Build Hotel depot — one per day for multi-day trips
        hotels = []
        for day_idx in range(contract.num_days):
            hotels.append({
                "id": f"hotel_day_{day_idx}",
                "name": contract.hotel_name,
                "location": {
                    "latitude": contract.hotel_lat,
                    "longitude": contract.hotel_lon,
                },
                "assigned_days": [day_idx],
            })

        # Build Constraints
        constraints = {
            "num_days": contract.num_days,
            "budget_total": contract.budget_max,
            "transport_modes": transport_modes_from_contract(contract),
        }

        return {
            "pois": l4_pois,
            "hotels": hotels,
            "constraints": constraints,
        }

    def _re_route_constraints(self, original_itinerary: dict, day_index: int) -> Dict:
        """Prefer transport modes stored on original itinerary; fallback to taxi+walking."""
        stored = original_itinerary.get("constraints", {})
        modes = stored.get("transport_modes")
        if isinstance(modes, list) and modes:
            return {"num_days": 1, "transport_modes": modes}
        walking = original_itinerary.get("walking_tolerance")
        if walking:
            contract = LLMDataContract(walking_tolerance=walking, num_days=1)
            return {"num_days": 1, "transport_modes": transport_modes_from_contract(contract)}
        return {"num_days": 1, "transport_modes": ["taxi", "walking"]}

    async def plan(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan (blocking)."""
        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/plan",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Layer 4 call failed: {e}")
            return None

    async def plan_stream(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ):
        """SSE streaming: call Layer 4 /plan then yield result as SSE event.

        Layer 4 returns a single JSON response (not a stream), so we call
        plan() and wrap the result in an SSE-compatible format that the
        mobile client expects (data.status === 'success' || data.days).
        """
        import json as json_lib

        result = await self.plan(pois=pois, contract=contract, time_limit=time_limit)

        if result is None:
            yield f"data: {json_lib.dumps({'step': 'error', 'message': 'Layer 4 solver unavailable'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        yield f"data: {json_lib.dumps(result)}\n\n"
        yield "data: [DONE]\n\n"

    async def re_route(
        self,
        current_lat: float,
        current_lon: float,
        current_time_min: int,
        remaining_poi_ids: list[str],
        original_itinerary: dict,
        day_index: int,
        excluded_poi_ids: list[str] | None = None,
        time_limit: int = 15,
    ) -> dict | None:
        """Forward re-route request to Layer 4 POST /re-route.

        Extracts POI objects and hotel/constraints from the original
        itinerary and builds a Layer 4 ReRouteRequest payload.
        """
        # Extract the target day from original itinerary
        days = original_itinerary.get("days", [])
        target_day = None
        for d in days:
            if d.get("day_index") == day_index:
                target_day = d
                break
        if target_day is None and days:
            target_day = days[min(day_index, len(days) - 1)]

        if target_day is None:
            logger.error("No day found in original itinerary for re-route")
            return None

        # Build POI objects from stops in the target day
        # Layer 4 needs full POI objects, not just IDs
        pois = []
        for stop in target_day.get("stops", []):
            pois.append({
                "id": stop["poi_id"],
                "name": stop["poi_name"],
                "category": "general",
                "location": stop["location"],
                "visit_duration_min": stop.get("visit_duration_min", 60),
                "entrance_fee": stop.get("entrance_fee", 0),
                "priority_score": 0.8,
            })

        # Build hotel from day's hotel info (support both v1 and v2 field names)
        hotel_name = target_day.get("end_hotel_name") or target_day.get("start_hotel_name") or target_day.get("hotel_name", "Hotel")
        hotel_location = target_day.get("end_hotel_location") or target_day.get("start_hotel_location") or target_day.get("hotel_location", {
            "latitude": current_lat,
            "longitude": current_lon,
        })
        hotel = {
            "id": f"hotel_day_{day_index}",
            "name": hotel_name,
            "location": hotel_location,
        }

        # Build day plan
        day_plan = {
            "day_index": day_index,
            "date": target_day.get("date", "re-route"),
            "start_time_min": current_time_min,
            "end_time_min": 1260,  # 21:00
        }

        # Build constraints
        constraints = self._re_route_constraints(original_itinerary, day_index)

        # Assemble Layer 4 ReRouteRequest
        payload = {
            "current_location": {
                "latitude": current_lat,
                "longitude": current_lon,
            },
            "current_time_min": current_time_min,
            "remaining_poi_ids": remaining_poi_ids,
            "pois": pois,
            "hotel": hotel,
            "day": day_plan,
            "constraints": constraints,
            "excluded_poi_ids": excluded_poi_ids,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/re-route",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Layer 4 re-route failed: {e}")
            return None

