"""TravelPlanService — orchestrates the Two-Stage travel solver.

Flow:
  1. Auto-generate DayPlans if not provided
  2. Resolve hotels for each day
  3. Stage 1: POIAllocator assigns POIs to days
  4. Stage 2: TravelSolverAdapter solves each day's route
  5. Assemble TravelItinerary response

Re-route Flow (JIT):
  1. Receive current_location + remaining POIs
  2. Create virtual depot at current_location
  3. Solve only for remaining POIs from current time
  4. Return updated TravelItineraryDay
"""

import threading
from typing import List, Optional, Dict
from ..models.domain import (
    POI, Hotel, DayPlan, Location, TravelConstraints, TransportMode,
    TravelItinerary, TravelItineraryDay,
)
from ..models.api import TravelPlanRequest, ReRouteRequest
from .poi_allocator import POIAllocator
from .travel_solver import TravelSolverAdapter
from .distance_cache import DistanceCacheService
from ..config import get_logger

logger = get_logger(__name__)


class TravelPlanService:
    """Orchestrates travel itinerary planning."""

    def __init__(self):
        self.allocator = POIAllocator()
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
        time_limit_per_day: int = 30,
        solver_type: str = "ortools",
    ) -> TravelItinerary:
        """Create optimized travel itinerary (thread-safe)."""
        if not self._lock.acquire(timeout=60.0):
            raise ValueError("Travel solver is busy. Request timed out in queue.")

        try:
            self._is_busy = True
            return self._plan_impl(request, time_limit_per_day, solver_type)
        finally:
            self._is_busy = False
            self._lock.release()

    def _plan_impl(
        self,
        request: TravelPlanRequest,
        time_limit_per_day: int = 30,
        solver_type: str = "ortools",
    ) -> TravelItinerary:
        """Internal plan implementation."""
        # 0. Fetch real distances from OSRM
        all_locs = [h.location for h in request.hotels] + [p.location for p in request.pois]
        logger.info(f"Prefetching distance matrix for {len(all_locs)} unique locations")

        mode = request.constraints.transport_modes[0] if request.constraints.transport_modes else TransportMode.TAXI
        matrix = self.distance_cache.build_matrix(all_locs, mode)

        # 1. Generate day plans if not provided
        day_plans = request.day_plans or self._generate_day_plans(request)

        # 2. Build hotel map
        hotel_map = {h.id: h for h in request.hotels}

        # 3. Stage 1: Allocate POIs to days
        logger.info("Stage 1: Allocating POIs to days...")
        allocation = self.allocator.allocate(
            request.pois, request.hotels, day_plans, request.constraints
        )

        # Build POI lookup
        poi_map = {p.id: p for p in request.pois}

        # 4. Stage 2: Solve each day
        logger.info("Stage 2: Solving routes per day...")
        days_result: List[TravelItineraryDay] = []

        for day in day_plans:
            hotel = self._resolve_hotel(request.hotels, day.day_index)
            poi_ids = allocation.day_assignments.get(day.day_index, [])
            day_pois = [poi_map[pid] for pid in poi_ids if pid in poi_map]

            logger.info(
                f"Day {day.day_index} ({day.date}): "
                f"{len(day_pois)} POIs, hotel={hotel.name}"
            )

            day_result = self.solver.solve_day(
                pois=day_pois,
                hotel=hotel,
                day=day,
                time_limit=time_limit_per_day,
                solver_type=solver_type,
                matrix=matrix,
            )

            if day_result:
                days_result.append(day_result)
            else:
                days_result.append(TravelItineraryDay(
                    day_index=day.day_index, date=day.date,
                    hotel_name=hotel.name, hotel_location=hotel.location,
                    stops=[], total_travel_min=0, total_visit_min=0,
                    total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                ))

        # 5. Assemble response
        total_pois = sum(d.num_pois for d in days_result)
        total_fee = sum(d.total_entrance_fee for d in days_result)
        total_travel = sum(d.total_travel_min for d in days_result)
        total_dist = sum(d.total_distance_km for d in days_result)

        # Collect dropped POIs
        dropped_pois = [
            {"poi_id": pid, "reason": allocation.dropped_reasons.get(pid, "unknown")}
            for pid in allocation.dropped_poi_ids
        ]
        
        # Add POIs dropped by solver (Stage 2)
        visited_poi_ids = {stop.poi_id for day in days_result for stop in day.stops}
        solver_dropped = [p.id for p in request.pois if p.id not in visited_poi_ids and p.id not in allocation.dropped_poi_ids]
        
        for pid in solver_dropped:
            dropped_pois.append({"poi_id": pid, "reason": "solver_time_window_violation"})

        total_dropped = len(request.pois) - total_pois

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
        )

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
        all_locs = [request.current_location] + [p.location for p in remaining]
        mode = request.constraints.transport_modes[0] if request.constraints.transport_modes else TransportMode.TAXI
        matrix = self.distance_cache.build_matrix(all_locs, mode)

        # 5. Solve
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
            hotel_name="Current Location",
            hotel_location=request.current_location,
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
