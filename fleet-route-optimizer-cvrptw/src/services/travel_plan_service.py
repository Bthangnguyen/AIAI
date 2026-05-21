"""TravelPlanService — orchestrates the multi-depot travel solver (v2).

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

import threading
from typing import List, Optional, Dict
from ..models.domain import (
    POI, Hotel, DayPlan, Location, TravelConstraints, TransportMode,
    TravelItinerary, TravelItineraryDay,
)
from ..models.api import TravelPlanRequest, ReRouteRequest
from .travel_solver import TravelSolverAdapter
from .distance_cache import DistanceCacheService
from .itinerary_validator import ItineraryValidator
from .rest_inserter import RestBreakInserter
from ..config import get_logger

logger = get_logger(__name__)

MAX_BUDGET_RETRIES = 3


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

        # 3. Solve trip (multi-depot, all days at once)
        logger.info(f"Solving multi-depot trip: {len(request.pois)} POIs, {len(day_plans)} days")
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
        days_result = self._validate_budget(
            days_result, pois, request.hotels, day_plans,
            request.constraints, matrix, time_limit, solver_type
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
            days_result[i] = rest_inserter.insert_breaks(
                day, poi_map,
                rest_interval_min=rest_interval,
                rest_duration_min=rest_duration,
            )

        # 7. Assemble response
        total_pois = sum(d.num_pois for d in days_result)
        total_fee = sum(d.total_entrance_fee for d in days_result)
        total_travel = sum(d.total_travel_min for d in days_result)
        total_dist = sum(d.total_distance_km for d in days_result)

        # Collect dropped POIs
        visited_poi_ids = {stop.poi_id for day in days_result for stop in day.stops if stop.poi_id != "__rest_break__"}
        dropped_pois = [
            {"poi_id": p.id, "reason": "solver_dropped"}
            for p in request.pois if p.id not in visited_poi_ids
        ]
        total_dropped = len(request.pois) - len(visited_poi_ids)

        return TravelItinerary(
            status="success",
            num_days=len(days_result),
            days=days_result,
            total_pois_visited=total_pois,
            total_pois_dropped=total_dropped,
            total_entrance_fee=total_fee,
            total_travel_min=total_travel,
            total_distance_km=round(total_dist, 2),
            budget_total=request.constraints.budget_total,
            budget_used=total_fee,
            dropped_pois=dropped_pois if dropped_pois else None,
            solver=solver_type,
            validation_notes=validation_notes if validation_notes else None,
        )

    def _validate_budget(
        self,
        days_result: List[TravelItineraryDay],
        pois: List[POI],
        hotels: List[Hotel],
        day_plans: List[DayPlan],
        constraints: TravelConstraints,
        matrix: Dict,
        time_limit: int,
        solver_type: str,
    ) -> List[TravelItineraryDay]:
        """Post-solve global budget validation with retry.

        If total entrance fees exceed budget_total, drop lowest-priority
        non-locked non-meal POIs and re-solve. Max 3 retries.
        """
        budget = constraints.budget_total
        if not budget:
            return days_result

        for attempt in range(MAX_BUDGET_RETRIES):
            total_fee = sum(d.total_entrance_fee for d in days_result)

            if total_fee <= budget:
                logger.info(f"Budget OK: {total_fee:.0f} ≤ {budget:.0f}")
                return days_result

            logger.warning(
                f"Budget exceeded ({total_fee:.0f} > {budget:.0f}), "
                f"attempt {attempt + 1}/{MAX_BUDGET_RETRIES}"
            )

            # Find droppable POIs (not locked, not meal, has fee)
            visited_ids = {stop.poi_id for day in days_result for stop in day.stops}
            droppable = [
                p for p in pois
                if p.id in visited_ids
                and not p.is_locked
                and p.meal_type is None
                and p.entrance_fee > 0
            ]
            droppable.sort(key=lambda p: p.priority_score)

            if not droppable:
                logger.warning("No droppable POIs left, returning best solution")
                return days_result

            # Drop lowest priority POI
            drop = droppable[0]
            logger.info(f"Dropping POI '{drop.name}' (fee={drop.entrance_fee}, priority={drop.priority_score})")
            pois = [p for p in pois if p.id != drop.id]

            # Re-solve
            new_result = self.solver.solve_trip(
                pois=pois, hotels=hotels, days=day_plans,
                matrix=matrix, time_limit=time_limit, solver_type=solver_type,
            )

            if new_result:
                days_result = new_result

        return days_result

    def re_route(self, request: ReRouteRequest, time_limit: int = 15, solver_type: str = "ortools") -> TravelItineraryDay:
        """Re-route remaining POIs from current location (JIT).

        Creates a virtual depot at the traveler's current position and
        solves only for the remaining unvisited POIs.
        """
        if not self._lock.acquire(blocking=False):
            raise ValueError("Travel solver is already running. Try again later.")

        try:
            self._is_busy = True
            return self._re_route_impl(request, time_limit, solver_type)
        finally:
            self._is_busy = False
            self._lock.release()

    def _re_route_impl(self, request: ReRouteRequest, time_limit: int, solver_type: str) -> TravelItineraryDay:
        # 1. Filter POIs
        poi_map = {p.id: p for p in request.pois}
        remaining = [poi_map[pid] for pid in request.remaining_poi_ids if pid in poi_map]

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

