"""HTTP client for Layer 4 (OR-Tools Routing Engine)."""

import httpx
import time
from typing import Optional, Dict, List
from app.config import settings
from app.schemas.trip import POIResponse, LLMDataContract
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_time:
                self.state = "HALF-OPEN"
                logger.info("Circuit Breaker transitioned to HALF-OPEN")
        return self.state

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_state_change = time.time()
        logger.info("Circuit Breaker transitioned to CLOSED (success recorded)")

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"Circuit Breaker failure recorded. Count: {self.failure_count}/{self.failure_threshold}")
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error("Circuit Breaker transitioned to OPEN (threshold exceeded)")


# Global circuit breaker instance
solver_breaker = CircuitBreaker()


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
            "transport_modes": ["taxi", "walking"],
        }

        return {
            "pois": l4_pois,
            "hotels": hotels,
            "constraints": constraints,
        }

    async def plan(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan (blocking)."""
        state = solver_breaker.check_state()
        if state == "OPEN":
            logger.error("Circuit breaker is OPEN. Blocking request to Layer 4 Solver.")
            return {"error_code": "CIRCUIT_BREAKER_OPEN", "message": "Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây."}

        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=settings.SOLVER_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/plan",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                
                if resp.status_code == 400:
                    solver_breaker.record_success()
                    error_detail = resp.json().get("detail", {})
                    return {
                        "error_code": error_detail.get("error_code", "NO_FEASIBLE_ROUTE"),
                        "message": error_detail.get("message", "Lỗi lập lịch trình.")
                    }
                
                resp.raise_for_status()
                solver_breaker.record_success()
                return resp.json()
        except httpx.TimeoutException as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 call timed out: {e}")
            return {"error_code": "TIMEOUT", "message": "Quá thời gian phản hồi từ máy chủ lập lịch trình (120 giây)."}
        except httpx.HTTPStatusError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 HTTP error: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Lỗi hệ thống Solver: {e.response.status_code}"}
        except httpx.RequestError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 request error: {e}")
            return {"error_code": "OSRM_UNREACHABLE", "message": "Không thể kết nối đến máy chủ định tuyến."}
        except Exception as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 call failed: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Planning error: {str(e)}"}

    async def plan_stream(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
        hotel_fallback: bool = False,
    ):
        """SSE streaming: call Layer 4 /plan then yield result as SSE event."""
        import json as json_lib

        if hotel_fallback:
            logger.warning("🏨 [HOTEL_FALLBACK] User did not provide coordinates or selected hotel was invalid. System has automatically chosen a default/optimal hotel.")

        result = await self.plan(pois=pois, contract=contract, time_limit=time_limit)

        if result is None:
            yield f"data: {json_lib.dumps({'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': 'Layer 4 solver unavailable'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        if "error_code" in result:
            yield f"data: {json_lib.dumps({'step': 'error', 'error_code': result['error_code'], 'message': result['message']})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Inject hotel fallback attribute
        result["hotel_fallback"] = hotel_fallback

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
        constraints = {
            "num_days": 1,
            "transport_modes": ["taxi", "walking"],
        }

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

