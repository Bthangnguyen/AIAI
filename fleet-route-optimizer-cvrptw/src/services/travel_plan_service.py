"""TravelPlanService - orchestrates the multi-depot travel solver (v2).

Flow:
  1. Auto-generate DayPlans if not provided
  2. Resolve hotel start/end per day
  3. Call solve_trip() (multi-depot, all days in 1 OR-Tools model)
  4. Post-solve: global budget validation with retry
  5. Assemble TravelItinerary response

Re-route Flow (JIT):
  1. Receive current_location + remaining POIs
  2. Create virtual depot at current_location
  3. Solve only for remaining POIs from current time (single-depot)
  4. Return updated TravelItineraryDay
"""

import math
import threading
from typing import List, Optional, Dict, Any
from ..models.domain import (
    POI, Hotel, DayPlan, Location, TravelConstraints, TransportMode,
    TravelItinerary, TravelItineraryDay, TimeWindow,
)
from ..models.api import TravelPlanRequest, ReRouteRequest
from .travel_solver import TravelSolverAdapter
from .distance_cache import DistanceCacheService
from .itinerary_validator import ItineraryValidator
from .rest_inserter import RestBreakInserter
from ..config import get_logger
from ..utils.distance_calculator import haversine_distance

logger = get_logger(__name__)

MAX_BUDGET_RETRIES = 3
AVERAGE_TRAVEL_SPEED_KMH = 30.0
ROAD_FACTOR = 1.25


class TravelPlanService:
    """Orchestrates travel itinerary planning."""

    def __init__(self):
        self.solver = TravelSolverAdapter()
        self.distance_cache = DistanceCacheService()
        self._lock = threading.Lock()
        self._is_busy = False

    def is_busy(self) -> bool:
        """Check if solver is currently running."""
        return self._is_busy

    def plan(
        self,
        request: TravelPlanRequest,
        time_limit: int = 120,
        solver_type: str = "ortools",
    ) -> TravelItinerary:
        """Create optimized travel itinerary (thread-safe)."""
        if not self._lock.acquire(timeout=60.0):
            raise ValueError("Travel solver is busy. Request timed out in queue.")

        try:
            self._is_busy = True
            return self._plan_impl(request, time_limit, solver_type)
        finally:
            self._is_busy = False
            self._lock.release()

    def _plan_impl(
        self,
        request: TravelPlanRequest,
        time_limit: int = 120,
        solver_type: str = "ortools",
    ) -> TravelItinerary:
        """Internal plan implementation using multi-depot solver."""
        # 0. Fetch real distances from OSRM
        all_locs = [h.location for h in request.hotels] + [p.location for p in request.pois]
        logger.info(f"Prefetching distance matrix for {len(all_locs)} unique locations")

        mode = request.constraints.transport_modes[0] if request.constraints.transport_modes else TransportMode.TAXI
        matrix = self.distance_cache.build_matrix(all_locs, mode)

        # 1. Generate day plans if not provided
        day_plans = request.day_plans or self._generate_day_plans(request)

        # 2. Resolve hotel start/end per day
        self._resolve_hotel_transfers(day_plans, request.hotels)

        # 3. Solve trip
        skeleton = request.metadata.get("skeleton") if request.metadata else None

        if skeleton and "days" in skeleton:
            logger.info("🧠 LLM Hybrid: Running Skeleton-guided single-day optimization...")
            poi_lookup = {p.id: p for p in request.pois}
            days_result = []

            for day_plan in day_plans:
                day_idx = day_plan.day_index
                sk_day = next((d for d in skeleton["days"] if d["day_index"] == day_idx), None)

                if not sk_day or not sk_day.get("stops"):
                    # Empty day
                    start_hotel = self._resolve_hotel(request.hotels, day_idx)
                    days_result.append(TravelItineraryDay(
                        day_index=day_idx,
                        date=day_plan.date,
                        start_hotel_name=start_hotel.name if start_hotel else "Hotel",
                        start_hotel_location=start_hotel.location if start_hotel else None,
                        end_hotel_name=start_hotel.name if start_hotel else "Hotel",
                        end_hotel_location=start_hotel.location if start_hotel else None,
                        stops=[], total_travel_min=0, total_visit_min=0,
                        total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                        start_time_min=day_plan.start_time_min,
                        end_time_min=day_plan.end_time_min,
                    ))
                    continue

                day_pois = []
                for stop in sk_day["stops"]:
                    pid = stop.get("poi_id")
                    slot = stop.get("slot", "morning")
                    if pid in poi_lookup:
                        poi = poi_lookup[pid]
                        poi_copy = poi.model_copy()

                        # Apply slot bounds
                        slot_tw = self._get_slot_time_window(slot, day_plan.start_time_min, day_plan.end_time_min)
                        poi_copy.time_window = TimeWindow(start_min=slot_tw[0], end_min=slot_tw[1])

                        # Keep narrative context
                        poi_copy.description = stop.get("vibe_note") or poi_copy.description
                        day_pois.append(poi_copy)

                # Solve single day route
                day_results_single = self.solver.solve_trip(
                    pois=day_pois,
                    hotels=request.hotels,
                    days=[day_plan],
                    matrix=matrix,
                    time_limit=time_limit,
                    solver_type=solver_type,
                )

                if day_results_single and len(day_results_single) > 0:
                    days_result.append(day_results_single[0])
                else:
                    logger.warning(f"Solver failed to find a solution for Day {day_idx + 1} with {len(day_pois)} POIs. Trying without slot constraints...")
                    day_pois_fallback = [poi_lookup[s.get("poi_id")].model_copy() for s in sk_day["stops"] if s.get("poi_id") in poi_lookup]
                    day_results_single = self.solver.solve_trip(
                        pois=day_pois_fallback,
                        hotels=request.hotels,
                        days=[day_plan],
                        matrix=matrix,
                        time_limit=time_limit,
                        solver_type=solver_type,
                    )
                    if day_results_single:
                        days_result.append(day_results_single[0])
                    else:
                        start_hotel = self._resolve_hotel(request.hotels, day_idx)
                        days_result.append(TravelItineraryDay(
                            day_index=day_idx,
                            date=day_plan.date,
                            start_hotel_name=start_hotel.name if start_hotel else "Hotel",
                            start_hotel_location=start_hotel.location if start_hotel else None,
                            end_hotel_name=start_hotel.name if start_hotel else "Hotel",
                            end_hotel_location=start_hotel.location if start_hotel else None,
                            stops=[], total_travel_min=0, total_visit_min=0,
                            total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                            start_time_min=day_plan.start_time_min,
                            end_time_min=day_plan.end_time_min,
                        ))
        else:
            logger.info(f"Solving legacy multi-depot trip: {len(request.pois)} POIs, {len(day_plans)} days")
            pois = list(request.pois)

            days_result = self.solver.solve_trip(
                pois=pois,
                hotels=request.hotels,
                days=day_plans,
                matrix=matrix,
                time_limit=time_limit,
                solver_type=solver_type,
            )

        if not days_result:
            return TravelItinerary(
                status="error", num_days=0, days=[],
                total_pois_visited=0, message="Solver failed to find a solution",
            )

        # 4. Budget validation with retry
        pois = list(request.pois)
        days_result = self._validate_budget(
            days_result, pois, request.hotels, day_plans,
            request.constraints, matrix, time_limit, solver_type,
            skeleton=skeleton
        )

        # 5. Post-solve validation
        poi_map = {p.id: p for p in request.pois}
        validator = ItineraryValidator()
        validation = validator.validate(days_result, poi_map, {
            "max_consecutive_heavy": getattr(request.constraints, "max_consecutive_heavy", 2),
            "avoid_outdoor_start": 720,
            "avoid_outdoor_end": 840,
            "rest_interval_min": getattr(request.constraints, "rest_interval_min", 180),
        })
        validation_notes = []
        if validation.issues:
            logger.info(f"Validation: {len(validation.issues)} issues (score={validation.score:.2f})")
            for issue in validation.issues:
                logger.info(f"  [{issue.severity}] {issue.rule}: {issue.message}")
                validation_notes.append(f"[{issue.severity}] {issue.message}")

        # 6. Post-solve rest break insertion
        rest_inserter = RestBreakInserter()
        rest_interval = getattr(request.constraints, "rest_interval_min", 180)
        rest_duration = getattr(request.constraints, "rest_duration_min", 20)
        for i, day in enumerate(days_result):
            plan = next((p for p in day_plans if p.day_index == day.day_index), None)
            day = rest_inserter.apply_day_rhythm(day, poi_map, plan)
            day = rest_inserter.insert_meal_breaks(day, poi_map)
            day = rest_inserter.insert_food_tour_pacing(day, poi_map, plan)
            days_result[i] = rest_inserter.insert_breaks(
                day, poi_map,
                rest_interval_min=rest_interval,
                rest_duration_min=rest_duration,
            )

        # 7. Final timeline pass: expose conservative point-to-point travel
        # times and make all arrivals sequential. Use 30 km/h average speed so
        # the itinerary is intentionally less compressed than ideal routing.
        self._recompute_conservative_travel_times(days_result, matrix)

        # 8. Assemble response
        total_pois_visited = sum(len([s for s in day.stops if not str(s.poi_id).startswith("__")]) for day in days_result)
        total_pois_dropped = max(0, len(request.pois) - total_pois_visited)
        total_distance = sum(day.total_distance_km for day in days_result)
        total_travel = sum(day.total_travel_min for day in days_result)
        return TravelItinerary(
            status="success",
            num_days=len(days_result),
            days=days_result,
            total_pois_visited=total_pois_visited,
            total_pois_dropped=total_pois_dropped,
            total_distance_km=round(total_distance, 2),
            total_travel_min=total_travel,
            message="Itinerary planned successfully",
            validation_notes=validation_notes,
        )

    def re_route(
        self,
        request: ReRouteRequest,
        time_limit: int = 60,
        solver_type: str = "ortools",
    ) -> TravelItineraryDay:
        """JIT Re-routing flow from current location for remaining POIs (thread-safe)."""
        if not self._lock.acquire(timeout=60.0):
            raise ValueError("Travel solver is busy. Request timed out in queue.")

        try:
            self._is_busy = True
            remaining_ids = set(request.remaining_poi_ids)
            remaining = [p for p in request.pois if p.id in remaining_ids]

            # Remove excluded
            if request.excluded_poi_ids:
                excluded = set(request.excluded_poi_ids)
                remaining = [p for p in remaining if p.id not in excluded]

            # 2. Create virtual depot at current location
            virtual_hotel = Hotel(
                id="__current_location__",
                name="Current Location",
                location=request.current_location,
            )

            # 3. Override day start time to current time
            day = request.day.model_copy(update={"start_time_min": request.current_time_min})

            # 4. Fetch matrix for this small set
            all_locs = [request.current_location, request.hotel.location] + [p.location for p in remaining]
            mode = request.constraints.transport_modes[0] if request.constraints.transport_modes else TransportMode.TAXI
            matrix = self.distance_cache.build_matrix(all_locs, mode)

            # 5. Solve (single-depot: start=GPS, end=hotel)
            logger.info(f"Re-route: {len(remaining)} remaining POIs from ({request.current_location.latitude}, {request.current_location.longitude}) at t={request.current_time_min}")
            result = self.solver.solve_day(
                pois=remaining,
                hotel=virtual_hotel,
                day=day,
                time_limit=time_limit,
                solver_type=solver_type,
                matrix=matrix,
            )

            if result:
                self._recompute_conservative_travel_times([result], matrix)
                return result

            # Fallback: empty day
            return TravelItineraryDay(
                day_index=day.day_index, date=day.date,
                start_hotel_name="Current Location",
                start_hotel_location=request.current_location,
                end_hotel_name=request.hotel.name,
                end_hotel_location=request.hotel.location,
                stops=[], total_travel_min=0, total_visit_min=0,
                total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
            )
        finally:
            self._is_busy = False
            self._lock.release()

    def _generate_day_plans(self, request: TravelPlanRequest) -> List[DayPlan]:
        """Auto-generate DayPlans from constraints."""
        plans = []
        for i in range(request.constraints.num_days):
            hotel = self._resolve_hotel(request.hotels, i)
            plans.append(DayPlan(
                day_index=i,
                date=f"day-{i}",
                hotel_id=hotel.id if hotel else None,
            ))
        return plans

    def _resolve_hotel(self, hotels: List[Hotel], day_index: int) -> Hotel:
        """Find the hotel assigned to a specific day."""
        for hotel in hotels:
            if hotel.assigned_days and day_index in hotel.assigned_days:
                return hotel
        return hotels[0] if hotels else None

    def _resolve_hotel_transfers(self, day_plans: List[DayPlan], hotels: List[Hotel]) -> None:
        """Auto-fill start_hotel_id/end_hotel_id for hotel transfers.

        Rule: day N ends at hotel of day N+1 (if different).
        """
        for i, day in enumerate(day_plans):
            if not day.hotel_id:
                hotel = self._resolve_hotel(hotels, day.day_index)
                day.hotel_id = hotel.id if hotel else hotels[0].id

            if not day.start_hotel_id:
                day.start_hotel_id = day.hotel_id

            if not day.end_hotel_id:
                # Default: end at next day's start hotel
                if i + 1 < len(day_plans):
                    next_day = day_plans[i + 1]
                    next_hotel_id = next_day.hotel_id or next_day.start_hotel_id
                    if next_hotel_id:
                        day.end_hotel_id = next_hotel_id
                    else:
                        next_hotel = self._resolve_hotel(hotels, next_day.day_index)
                        day.end_hotel_id = next_hotel.id if next_hotel else day.hotel_id
                else:
                    day.end_hotel_id = day.hotel_id  # Last day: return to same hotel

    def _recompute_conservative_travel_times(
        self,
        days: List[TravelItineraryDay],
        matrix: Optional[Dict],
        speed_kmh: float = AVERAGE_TRAVEL_SPEED_KMH,
    ) -> None:
        """Retimes final itinerary using conservative 30 km/h travel estimates.

        Solver and post-processors may insert rest/meal stops after OR-Tools
        routing. This final pass is the source of truth for UI fields:
        travel_time_from_prev_min, travel_time_to_next_min, arrivals,
        departures, total_travel_min, and total_distance_km.
        """
        for day in days:
            if not day.stops:
                day.total_travel_min = 0
                day.total_distance_km = 0.0
                continue

            stops = sorted(day.stops, key=lambda s: (s.arrival_time_min, s.departure_time_min))
            prev_location = day.start_hotel_location
            prev_departure = day.start_time_min
            total_travel = 0
            total_distance = 0.0

            for stop in stops:
                distance_km = self._distance_between(prev_location, stop.location, matrix)
                travel_min = self._travel_minutes(distance_km, speed_kmh)
                stop.travel_time_from_prev_min = travel_min
                total_travel += travel_min
                total_distance += distance_km

                earliest_arrival = prev_departure + travel_min
                if stop.arrival_time_min < earliest_arrival:
                    stop.arrival_time_min = earliest_arrival
                    stop.departure_time_min = stop.arrival_time_min + stop.visit_duration_min

                prev_location = stop.location
                prev_departure = stop.departure_time_min

            for idx, stop in enumerate(stops):
                next_location = (
                    stops[idx + 1].location
                    if idx + 1 < len(stops)
                    else (day.end_hotel_location or day.start_hotel_location)
                )
                next_distance = self._distance_between(stop.location, next_location, matrix)
                stop.travel_time_to_next_min = self._travel_minutes(next_distance, speed_kmh)

            end_location = day.end_hotel_location or day.start_hotel_location
            total_travel += stops[-1].travel_time_to_next_min
            total_distance += self._distance_between(stops[-1].location, end_location, matrix)

            day.stops = stops
            day.total_travel_min = total_travel
            day.total_distance_km = round(total_distance, 2)
            day.total_visit_min = sum(
                s.visit_duration_min for s in stops
                if not str(s.poi_id).startswith("__")
            )
            day.num_pois = sum(1 for s in stops if not str(s.poi_id).startswith("__"))

    @staticmethod
    def _location_key(location: Location) -> tuple[float, float]:
        return (location.latitude, location.longitude)

    def _distance_between(
        self,
        from_location: Location,
        to_location: Location,
        matrix: Optional[Dict],
    ) -> float:
        if not from_location or not to_location:
            return 0.0

        from_key = self._location_key(from_location)
        to_key = self._location_key(to_location)
        if from_key == to_key:
            return 0.0

        if matrix:
            direct = matrix.get((from_key, to_key))
            if direct:
                return max(0.0, float(direct[0]))

        return max(0.0, haversine_distance(from_key, to_key) * ROAD_FACTOR)

    @staticmethod
    def _travel_minutes(distance_km: float, speed_kmh: float) -> int:
        if distance_km <= 0:
            return 0
        minutes = (distance_km / max(speed_kmh, 1.0)) * 60.0
        return max(3, int(math.ceil(minutes)))

    @staticmethod
    def _get_slot_time_window(slot: str, day_start: int, day_end: int) -> tuple[int, int]:
        slot = slot.lower().strip()
        if slot == "morning":
            start, end = 360, 720      # 06:00 - 12:00
        elif slot == "lunch":
            start, end = 690, 810      # 11:30 - 13:30
        elif slot == "afternoon":
            start, end = 780, 1080     # 13:00 - 18:00
        elif slot == "dinner":
            start, end = 1050, 1230    # 17:30 - 20:30
        elif slot == "evening":
            start, end = 1170, 1439    # 19:30 - 23:59
        else:
            start, end = day_start, day_end

        res_start = max(start, day_start)
        res_end = min(end, day_end)

        if res_start >= res_end:
            res_start = day_start
            res_end = day_end

        return res_start, res_end

    def _validate_budget(
        self,
        days_result: List[TravelItineraryDay],
        pois: List[POI],
        hotels: List[Hotel],
        day_plans: List[DayPlan],
        constraints: Any,
        matrix: Optional[Dict],
        time_limit: int,
        solver_type: str,
        skeleton: Optional[Dict] = None,
        max_retries: int = 3
    ) -> List[TravelItineraryDay]:
        """Validates that the generated itinerary respects the hard budget constraints.
        If it exceeds, drops the most expensive non-locked/non-meal POIs,
        applies Pace Relaxation (1.5x visit duration) for the remaining chill POIs,
        and re-solves using the single-day or multi-day solver.
        """
        budget_limit = getattr(constraints, "budget_total", None) or getattr(constraints, "budget_max", None)
        if not budget_limit:
            return days_result

        for attempt in range(max_retries):
            current_visited_poi_ids = set()
            total_entrance_fee = 0.0
            for day in days_result:
                for stop in day.stops:
                    if not str(stop.poi_id).startswith("__"):
                        current_visited_poi_ids.add(stop.poi_id)
                        total_entrance_fee += getattr(stop, "entrance_fee", 0.0) or 0.0

            if total_entrance_fee <= budget_limit:
                logger.info(f"Budget check PASSED on attempt {attempt}: {total_entrance_fee:,.0f} <= {budget_limit:,.0f}")
                return days_result

            logger.warning(
                f"Budget check FAILED on attempt {attempt}: {total_entrance_fee:,.0f} > {budget_limit:,.0f}. "
                f"Attempting to drop expensive POIs and relax pace..."
            )

            visited_pois = [p for p in pois if p.id in current_visited_poi_ids]
            
            candidates = []
            for p in visited_pois:
                is_locked = getattr(p, "is_locked", False)
                is_meal = getattr(p, "meal_type", None) is not None
                if not is_locked and not is_meal:
                    candidates.append(p)

            if not candidates:
                logger.warning("No flexible POI candidates left to drop to meet budget constraints!")
                return days_result

            candidates.sort(key=lambda p: (-(getattr(p, "entrance_fee", 0.0) or 0.0), getattr(p, "priority_score", 0.0)))
            poi_to_drop = candidates[0]
            poi_to_drop_id = poi_to_drop.id
            poi_to_drop_fee = getattr(poi_to_drop, "entrance_fee", 0.0) or 0.0

            logger.info(f"Dropping POI {poi_to_drop.name} (ID: {poi_to_drop_id}) to save {poi_to_drop_fee:,.0f} VND")

            pois = [p for p in pois if p.id != poi_to_drop_id]

            if skeleton and "days" in skeleton:
                for sk_day in skeleton["days"]:
                    if "stops" in sk_day:
                        sk_day["stops"] = [s for s in sk_day["stops"] if s.get("poi_id") != poi_to_drop_id]

            preferred_pace = getattr(constraints, "preferred_pace", "chill")
            if preferred_pace == "chill":
                logger.info("Preferred pace is chill. Applying 1.5x Pace Relaxation to remaining POIs...")
                for p in pois:
                    orig_duration = getattr(p, "visit_duration_min", 60)
                    p.visit_duration_min = int(orig_duration * 1.5)

            poi_lookup = {p.id: p for p in pois}
            
            if skeleton and "days" in skeleton:
                logger.info("🧠 Re-solving using Skeleton-guided Single-Day Routing...")
                new_days_result = []
                for day_idx, day_plan in enumerate(day_plans):
                    sk_day = next((d for d in skeleton["days"] if d.get("day_index") == day_idx), None)
                    if not sk_day or not sk_day.get("stops"):
                        start_hotel = self._resolve_hotel(hotels, day_idx)
                        new_days_result.append(TravelItineraryDay(
                            day_index=day_idx,
                            date=day_plan.date,
                            start_hotel_name=start_hotel.name if start_hotel else "Hotel",
                            start_hotel_location=start_hotel.location if start_hotel else None,
                            end_hotel_name=start_hotel.name if start_hotel else "Hotel",
                            end_hotel_location=start_hotel.location if start_hotel else None,
                            stops=[], total_travel_min=0, total_visit_min=0,
                            total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                            start_time_min=day_plan.start_time_min,
                            end_time_min=day_plan.end_time_min,
                        ))
                        continue

                    day_pois = []
                    for stop in sk_day["stops"]:
                        pid = stop.get("poi_id")
                        slot = stop.get("slot", "morning")
                        if pid in poi_lookup:
                            poi_copy = poi_lookup[pid].model_copy()
                            slot_tw = self._get_slot_time_window(slot, day_plan.start_time_min, day_plan.end_time_min)
                            poi_copy.time_window = TimeWindow(start_min=slot_tw[0], end_min=slot_tw[1])
                            poi_copy.description = stop.get("vibe_note") or poi_copy.description
                            day_pois.append(poi_copy)

                    day_results_single = self.solver.solve_trip(
                        pois=day_pois,
                        hotels=hotels,
                        days=[day_plan],
                        matrix=matrix,
                        time_limit=time_limit,
                        solver_type=solver_type,
                    )
                    if day_results_single and len(day_results_single) > 0:
                        new_days_result.append(day_results_single[0])
                    else:
                        day_pois_fallback = [poi_lookup[s.get("poi_id")].model_copy() for s in sk_day["stops"] if s.get("poi_id") in poi_lookup]
                        day_results_single = self.solver.solve_trip(
                            pois=day_pois_fallback,
                            hotels=hotels,
                            days=[day_plan],
                            matrix=matrix,
                            time_limit=time_limit,
                            solver_type=solver_type,
                        )
                        if day_results_single:
                            new_days_result.append(day_results_single[0])
                        else:
                            start_hotel = self._resolve_hotel(hotels, day_idx)
                            new_days_result.append(TravelItineraryDay(
                                day_index=day_idx,
                                date=day_plan.date,
                                start_hotel_name=start_hotel.name if start_hotel else "Hotel",
                                start_hotel_location=start_hotel.location if start_hotel else None,
                                end_hotel_name=start_hotel.name if start_hotel else "Hotel",
                                end_hotel_location=start_hotel.location if start_hotel else None,
                                stops=[], total_travel_min=0, total_visit_min=0,
                                total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                                start_time_min=day_plan.start_time_min,
                                end_time_min=day_plan.end_time_min,
                            ))
                days_result = new_days_result
            else:
                logger.info("Re-solving using legacy multi-depot solver...")
                days_result = self.solver.solve_trip(
                    pois=pois,
                    hotels=hotels,
                    days=day_plans,
                    matrix=matrix,
                    time_limit=time_limit,
                    solver_type=solver_type,
                )

        return days_result
