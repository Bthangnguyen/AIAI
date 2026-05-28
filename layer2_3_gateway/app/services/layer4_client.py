"""HTTP client for Layer 4 (OR-Tools Routing Engine)."""

import httpx
import json as json_lib
import time
import uuid
from typing import Optional, Dict, List
from app.config import settings
from app.schemas.trip import POIResponse, LLMDataContract
from app.utils.logging import AppLogger
from app.services.transport_modes import transport_modes_from_contract

logger = AppLogger().get_logger()


class UUIDEncoder(json_lib.JSONEncoder):
    """JSON encoder that safely converts UUID objects to strings."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def json_dumps(obj, **kwargs):
    """UUID-safe json.dumps wrapper."""
    return json_lib.dumps(obj, cls=UUIDEncoder, **kwargs)


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

    @staticmethod
    def _normalize_transport_modes(modes: List[str] | None) -> List[str]:
        """Map conversational transport names to Layer 4's supported enum values."""
        supported = {"walking", "taxi", "bus"}
        aliases = {
            "walk": "walking",
            "foot": "walking",
            "on_foot": "walking",
            "car": "taxi",
            "oto": "taxi",
            "o_to": "taxi",
            "private_car": "taxi",
            "motorbike": "taxi",
            "scooter": "taxi",
            "xe_may": "taxi",
            "xe máy": "taxi",
            "bus": "bus",
            "xe_buyt": "bus",
            "xe buýt": "bus",
        }
        normalized: List[str] = []
        for raw in modes or []:
            key = str(raw).strip().lower().replace(" ", "_")
            mode = aliases.get(key, key)
            if mode in supported and mode not in normalized:
                normalized.append(mode)
        return normalized or ["taxi", "walking"]

    def _build_payload(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
    ) -> Dict:
        """Assemble TravelPlanRequest matching Layer 4 schema exactly."""
        l4_pois = []
        for p in pois:
            l4_pois.append({
                "id": str(p.uuid),
                "name": p.name,
                "category": (p.category_group or p.category),
                "location": {"latitude": p.latitude, "longitude": p.longitude},
                "visit_duration_min": p.visit_duration_min,
                "time_window": {
                    "start_min": p.open_time,
                    "end_min": p.close_time,
                },
                "entrance_fee": p.entrance_fee,
                "priority_score": getattr(p, "utility_score", 1.0),
                "tags": p.tags or [],
                "description": p.description,
                "is_locked": p.is_locked,
            })

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

        # Integrate transport extraction & normalization
        contract_modes = transport_modes_from_contract(contract)
        normalized_modes = self._normalize_transport_modes(contract_modes)

        constraints = {
            "num_days": contract.num_days,
            "budget_total": None if getattr(contract, "budget_is_unlimited", False) else contract.budget_max,
            "transport_modes": normalized_modes,
            "target_category_distribution": contract.target_category_distribution,
        }

        # Ensure distribution is never None — use balanced default
        if not constraints["target_category_distribution"]:
            constraints["target_category_distribution"] = {
                "food": 0.35, "culture": 0.35, "nature": 0.20,
                "nightlife": 0.05, "adventure": 0.05
            }

        payload = {
            "pois": l4_pois,
            "hotels": hotels,
            "constraints": constraints,
        }

        # Hard cap: max 6 POIs per day, minimum 3 (for full_day/evening slot) or 2 (for short slots)
        max_pois_per_day = 6
        if getattr(contract, "estimated_pois", None) is not None:
            # Use ceiling division to prevent rounding down (e.g. 5 POIs in 2 days -> 3 per day, not 2)
            calculated_max = (contract.estimated_pois + contract.num_days - 1) // contract.num_days
            # Add a generous buffer if user requested a full day or food tour to allow adding outdoor/nature stops
            is_full_or_tour = (
                getattr(contract, "time_slot", None) == "full_day"
                or getattr(contract, "trip_type", None) == "food_tour"
                or getattr(contract, "trip_duration_hours", 0) >= 6
            )
            if is_full_or_tour:
                max_pois_per_day = min(6, max(4, calculated_max + 1))
            else:
                max_pois_per_day = min(6, max(2, calculated_max))

        payload["day_plans"] = [
            {
                "day_index": day_idx,
                "date": f"Day {day_idx + 1}",
                "hotel_id": f"hotel_day_{day_idx}",
                "start_time_min": contract.time_window.start_min if getattr(contract, "time_window", None) is not None else 480,
                "end_time_min": contract.time_window.end_min if getattr(contract, "time_window", None) is not None else 1260,
                "max_pois": max_pois_per_day,
            }
            for day_idx in range(contract.num_days)
        ]

        return payload

    def _re_route_constraints(self, original_itinerary: dict, day_index: int) -> Dict:
        """Prefer transport modes stored on original itinerary; fallback to taxi+walking."""
        stored = original_itinerary.get("constraints", {})
        modes = stored.get("transport_modes")
        if isinstance(modes, list) and modes:
            return {"num_days": 1, "transport_modes": modes}
        
        walking = original_itinerary.get("walking_tolerance")
        if walking:
            contract = LLMDataContract(walking_tolerance=walking, num_days=1)
            extracted_modes = transport_modes_from_contract(contract)
            return {"num_days": 1, "transport_modes": self._normalize_transport_modes(extracted_modes)}
        
        return {"num_days": 1, "transport_modes": ["taxi", "walking"]}

    async def plan(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan (blocking) under Circuit Breaker protection."""
        state = solver_breaker.check_state()
        if state == "OPEN":
            logger.error("Circuit breaker is OPEN. Blocking request to Layer 4 Solver.")
            return {"error_code": "CIRCUIT_BREAKER_OPEN", "message": "Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây."}

        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                result = resp.json()
                if result and "days" in result:
                    poi_map = {str(p.uuid): p for p in pois}
                    for day in result["days"]:
                        if "stops" in day:
                            for stop in day["stops"]:
                                poi_id = stop.get("poi_id")
                                if poi_id in poi_map:
                                    poi = poi_map[poi_id]
                                    stop["category"] = poi.category
                                    stop["description"] = poi.description

                # Run post-solver LLM itinerary validation layer
                if result and result.get("status") != "error" and "days" in result:
                    from app.services.itinerary_validator import ItineraryValidatorService
                    validator = ItineraryValidatorService()
                    result = await validator.validate_and_adjust(
                        l4_result=result,
                        contract=contract,
                        all_pois=pois
                    )

                return result
        except httpx.TimeoutException as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 call timed out: {e}")
            return {"error_code": "TIMEOUT", "message": "Quá thời gian phản hồi từ máy chủ lập lịch trình."}
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
        # json_lib and json_dumps already imported at module level

        if hotel_fallback:
            logger.warning("🏨 [HOTEL_FALLBACK] Selected optimal hotel default chosen by spatial criteria.")

        result = await self.plan(pois=pois, contract=contract, time_limit=time_limit)

        if result is None:
            yield f"data: {json_dumps({'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': 'Layer 4 solver unavailable'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        if "error_code" in result:
            yield f"data: {json_dumps({'step': 'error', 'error_code': result['error_code'], 'message': result['message']})}\n\n"
            yield "data: [DONE]\n\n"
            return

        result["hotel_fallback"] = hotel_fallback
        yield f"data: {json_dumps(result)}\n\n"
        yield "data: [DONE]\n\n"

    async def plan_alternatives(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan-multi under Circuit Breaker protection."""
        state = solver_breaker.check_state()
        if state == "OPEN":
            logger.error("Circuit breaker is OPEN. Blocking request to Layer 4 alternatives.")
            return {"error_code": "CIRCUIT_BREAKER_OPEN", "message": "Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây."}

        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{self.base_url}/plan-multi",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                
                if resp.status_code == 400:
                    solver_breaker.record_success()
                    error_detail = resp.json().get("detail", {})
                    return {
                        "error_code": error_detail.get("error_code", "NO_FEASIBLE_ROUTE"),
                        "message": error_detail.get("message", "Lỗi lập lịch trình thay thế.")
                    }
                
                resp.raise_for_status()
                solver_breaker.record_success()
                result = resp.json()
                if result and "plans" in result:
                    poi_map = {str(p.uuid): p for p in pois}
                    for plan in result["plans"]:
                        if "days" in plan:
                            for day in plan["days"]:
                                if "stops" in day:
                                    for stop in day["stops"]:
                                        poi_id = stop.get("poi_id")
                                        if poi_id in poi_map:
                                            poi = poi_map[poi_id]
                                            stop["category"] = poi.category
                                            stop["description"] = poi.description
                return result
        except httpx.TimeoutException as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi timed out: {e}")
            return {"error_code": "TIMEOUT", "message": "Quá thời gian phản hồi máy chủ."}
        except httpx.HTTPStatusError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi HTTP error: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Solver error: {e.response.status_code}"}
        except httpx.RequestError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi network error: {e}")
            return {"error_code": "OSRM_UNREACHABLE", "message": "Không kết nối được máy chủ định tuyến."}
        except Exception as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi failed: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": str(e)}

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
        """Forward re-route request to Layer 4 POST /re-route."""
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

        day_plan = {
            "day_index": day_index,
            "date": target_day.get("date", "re-route"),
            "start_time_min": current_time_min,
            "end_time_min": 1260,  # 21:00
        }

        # Resolve itinerary-aware rerouting constraints
        constraints = self._re_route_constraints(original_itinerary, day_index)

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
                result = resp.json()
                if result and "stops" in result:
                    stop_map = {s.get("poi_id"): s for s in target_day.get("stops", []) if isinstance(s, dict)}
                    for stop in result["stops"]:
                        poi_id = stop.get("poi_id")
                        if poi_id in stop_map:
                            orig = stop_map[poi_id]
                            stop["category"] = orig.get("category")
                            stop["description"] = orig.get("description")
                return result
        except httpx.HTTPError as e:
            logger.error(f"Layer 4 re-route failed: {e}")
            return None
