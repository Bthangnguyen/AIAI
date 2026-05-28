"""Travel Solver Adapter — converts travel domain to CVRPTW solver input.

Supports both:
- solve_trip(): Multi-depot, multi-day (v2 — all days in 1 model)
- solve_day(): Single-depot, single-day (v1 — used for re-route)
"""

from typing import List, Dict, Optional
from ..models.domain import (
    POI, Hotel, DayPlan, Location,
    TravelItineraryStop, TravelItineraryDay,
)
from ..core.solvers import create_solver
from ..config import get_logger

logger = get_logger(__name__)

# Category → Intensity mapping
INTENSITY_MAP = {
    "temple": "heavy", "palace": "heavy", "heritage": "heavy", "hiking": "heavy",
    "cafe": "light", "restaurant": "light", "night_market": "light",
    "spa": "light", "shopping": "light",
}

def get_intensity(category: str) -> str:
    """Map POI category to intensity level for rhythm penalty."""
    return INTENSITY_MAP.get(category.lower(), "medium")

def compute_fatigue_cost(poi) -> int:
    """Compute fatigue cost from intensity × duration. Always positive."""
    intensity = poi.intensity if poi.intensity != "medium" else get_intensity(poi.category)
    base = {"light": 1.0, "medium": 2.0, "heavy": 3.0}.get(intensity, 2.0)
    duration_factor = poi.visit_duration_min / 60.0
    return max(1, round(base * duration_factor))


class TravelSolverAdapter:
    """Adapts travel models to CVRPTW solver input and interprets output."""

    # ──────────────────────────────────────────────
    # v2: Multi-depot, multi-day
    # ──────────────────────────────────────────────

    def solve_trip(
        self,
        pois: List[POI],
        hotels: List[Hotel],
        days: List[DayPlan],
        matrix: Optional[Dict] = None,
        time_limit: int = 120,
        solver_type: str = "ortools",
        **kwargs,
    ) -> Optional[List[TravelItineraryDay]]:
        """Solve routing for entire trip using multi-depot model.

        Each day = 1 vehicle. OR-Tools assigns POIs to days and optimizes order.

        Args:
            pois: All candidate POIs (including meal POIs)
            hotels: Hotels for the trip
            days: DayPlans with per-day constraints
            matrix: Pre-computed distance/duration matrix {(loc_i, loc_j): (dist, dur)}
            time_limit: Solver time limit (seconds)

        Returns:
            List of TravelItineraryDay, one per day, or None
        """
        if not pois or not days:
            return None

        hotel_map = {h.id: h for h in hotels}
        num_days = len(days)

        # === Build node list: hotels first, then POIs ===
        # Collect unique hotel nodes needed
        hotel_nodes = []  # (hotel_id, hotel_obj)
        hotel_id_to_node = {}

        for day in days:
            start_hid = day.start_hotel_id or day.hotel_id
            end_hid = day.end_hotel_id or day.hotel_id
            for hid in [start_hid, end_hid]:
                if hid and hid not in hotel_id_to_node:
                    hotel_id_to_node[hid] = len(hotel_nodes)
                    hotel_nodes.append((hid, hotel_map[hid]))

        num_hotel_nodes = len(hotel_nodes)

        # Build starts/ends arrays
        starts = []
        ends = []
        for day in days:
            start_hid = day.start_hotel_id or day.hotel_id
            end_hid = day.end_hotel_id or day.hotel_id
            starts.append(hotel_id_to_node[start_hid])
            ends.append(hotel_id_to_node[end_hid])

        # Build locations array: hotels + POIs
        locations = [h[1].location.as_tuple() for h in hotel_nodes]
        locations += [poi.location.as_tuple() for poi in pois]

        # Demands: hotel=0, POI=visit_duration
        demands = [0] * num_hotel_nodes + [poi.visit_duration_min for poi in pois]

        # Time windows: hotels use widest day window, POIs use their own
        hotel_tw = {}
        for day in days:
            for hid in [day.start_hotel_id or day.hotel_id, day.end_hotel_id or day.hotel_id]:
                if hid not in hotel_tw:
                    hotel_tw[hid] = (day.start_time_min, day.end_time_min)
                else:
                    old = hotel_tw[hid]
                    hotel_tw[hid] = (min(old[0], day.start_time_min), max(old[1], day.end_time_min))

        time_windows = []
        for hid, _ in hotel_nodes:
            time_windows.append(hotel_tw[hid])
        for poi in pois:
            if poi.time_window:
                time_windows.append((poi.time_window.start_min, poi.time_window.end_min))
            else:
                time_windows.append((days[0].start_time_min, days[-1].end_time_min))

        # Vehicle capacities (per-day)
        vehicle_capacities = [day.max_daily_minutes for day in days]

        # Vehicle time windows (per-day)
        vehicle_time_windows = [(day.start_time_min, day.end_time_min) for day in days]

        # Locked list
        is_locked_list = [True] * num_hotel_nodes + [poi.is_locked for poi in pois]

        # Categories and intensities for diversity/rhythm penalties
        # Use macro category_group (food, cafe, culture...) instead of micro-category to catch streaks
        categories = [None] * num_hotel_nodes + [(poi.category_group or poi.category) for poi in pois]
        intensities = [None] * num_hotel_nodes + [
            poi.intensity if poi.intensity != "medium" else get_intensity(poi.category)
            for poi in pois
        ]

        # Meal assignments: {node_idx: vehicle_idx(day)}
        meal_assignments = {}
        for i, poi in enumerate(pois):
            if poi.meal_type and poi.assigned_day is not None:
                meal_assignments[num_hotel_nodes + i] = poi.assigned_day

        # Build problem_data
        problem = {
            "locations": locations,
            "demands": demands,
            "time_windows": time_windows,
            "vehicle_capacities": vehicle_capacities,
            "vehicle_time_windows": vehicle_time_windows,
            "num_vehicles": num_days,
            "starts": starts,
            "ends": ends,
            "service_time": 0,
            "coord_type": "latlon",
            "is_locked_list": is_locked_list,
            "categories": categories,
            "intensities": intensities,
            "meal_assignments": meal_assignments,
            "node_utilities": [0.0] * num_hotel_nodes + [poi.priority_score for poi in pois],
            "fatigue_costs": [0] * num_hotel_nodes + [
                poi.fatigue_cost if poi.fatigue_cost is not None else compute_fatigue_cost(poi)
                for poi in pois
            ],
            "max_fatigue_per_day": kwargs.get("max_fatigue_per_day", 15),
            "is_outdoor_list": [False] * num_hotel_nodes + [
                getattr(poi, "is_outdoor", False) for poi in pois
            ],
        }

        # Hard cap on stops per vehicle (day) — maps DayPlan.max_pois
        if days:
            max_stops = [d.max_pois for d in days]
            problem["max_stops_per_vehicle"] = max_stops

        # Inject distance/duration matrices if available
        if matrix:
            n = len(locations)
            dist_mx = [[0.0] * n for _ in range(n)]
            dur_mx = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    key = (locations[i], locations[j])
                    if key in matrix:
                        dist_mx[i][j], dur_mx[i][j] = matrix[key]
            problem["distance_matrix"] = dist_mx
            problem["duration_matrix"] = dur_mx

        # Solve
        poi_lookup = {num_hotel_nodes + i: pois[i] for i in range(len(pois))}

        try:
            solver = create_solver(solver_type, problem)
            solution = solver.solve(
                time_limit_seconds=time_limit,
                vehicle_penalty_weight=0,
                distance_weight=1.0,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Trip solver error: {e}")
            return None

        if not solution or solution.get("status") != "success":
            logger.warning("Trip solver: no solution found")
            return None

        # Extract per-day itineraries
        results = []
        routes = solution.get("routes", [])

        for vid in range(num_days):
            day = days[vid]
            start_hotel = hotel_nodes[starts[vid]][1]
            end_hotel = hotel_nodes[ends[vid]][1]

            # Find route for this vehicle
            vehicle_route = None
            for r in routes:
                if r.get("vehicle_id") == vid:
                    vehicle_route = r
                    break

            stops = []
            total_fee = 0.0

            if vehicle_route:
                for stop_data in vehicle_route.get("route", []):
                    loc_idx = stop_data.get("location", 0)
                    poi = poi_lookup.get(loc_idx)
                    if not poi:
                        continue  # skip hotel nodes
                    arrival = int(stop_data.get("time", 0))
                    stop = TravelItineraryStop(
                        poi_id=poi.id,
                        poi_name=poi.name,
                        location=poi.location,
                        arrival_time_min=arrival,
                        departure_time_min=arrival + poi.visit_duration_min,
                        visit_duration_min=poi.visit_duration_min,
                        travel_time_from_prev_min=0,
                        entrance_fee=poi.entrance_fee,
                    )
                    stops.append(stop)
                    total_fee += poi.entrance_fee

            results.append(TravelItineraryDay(
                day_index=day.day_index,
                date=day.date,
                start_hotel_name=start_hotel.name,
                start_hotel_location=start_hotel.location,
                end_hotel_name=end_hotel.name,
                end_hotel_location=end_hotel.location,
                stops=stops,
                total_travel_min=int(vehicle_route.get("travel_time_minutes", 0)) if vehicle_route else 0,
                total_visit_min=sum(s.visit_duration_min for s in stops),
                total_distance_km=round(vehicle_route.get("distance_km", 0.0), 2) if vehicle_route else 0.0,
                total_entrance_fee=total_fee,
                num_pois=len(stops),
                start_time_min=day.start_time_min,
                end_time_min=day.end_time_min,
            ))

        return results

    # ──────────────────────────────────────────────
    # v1: Single-depot, single-day (for re-route)
    # ──────────────────────────────────────────────

    def build_problem_data(
        self, 
        pois: List[POI], 
        hotel: Hotel, 
        day: DayPlan,
        matrix: Optional[Dict] = None
    ) -> Dict:
        """Convert travel models to solver-compatible ProblemData dict.

        Mapping:
        - Hotel → depot (index 0)
        - POIs → locations (index 1..N)
        - visit_duration_min → demand (capacity = max_daily_minutes)
        - POI.time_window → time_windows
        - service_time = 0 (visit_duration is in demand/capacity model)
        """
        # Locations: depot first, then POIs
        locations = [hotel.location.as_tuple()]
        locations += [poi.location.as_tuple() for poi in pois]

        # Demands: depot=0, POI=visit_duration_min
        demands = [0] + [poi.visit_duration_min for poi in pois]

        # Time windows
        depot_tw = (day.start_time_min, day.end_time_min)
        time_windows = [depot_tw]
        for poi in pois:
            if poi.time_window:
                time_windows.append((poi.time_window.start_min, poi.time_window.end_min))
            else:
                time_windows.append(depot_tw)

        # Locked points
        is_locked_list = [True] + [poi.is_locked for poi in pois]

        # Categories and intensities for diversity/rhythm penalties
        # Use macro category_group (food, cafe, culture...) instead of micro-category to catch streaks
        categories = [None] + [(poi.category_group or poi.category) for poi in pois]
        intensities = [None] + [
            poi.intensity if poi.intensity != "medium" else get_intensity(poi.category)
            for poi in pois
        ]

        problem = {
            "locations": locations,
            "demands": demands,
            "time_windows": time_windows,
            "vehicle_capacities": [day.max_daily_minutes],
            "num_vehicles": 1,
            "depot": 0,
            "service_time": 0,
            "coord_type": "latlon",
            "is_locked_list": is_locked_list,
            "categories": categories,
            "intensities": intensities,
            # Phase 0C: utility-based drop penalty
            "node_utilities": [0.0] + [poi.priority_score for poi in pois],
            # Phase 2A: fatigue dimension
            "fatigue_costs": [0] + [
                poi.fatigue_cost if poi.fatigue_cost is not None else compute_fatigue_cost(poi)
                for poi in pois
            ],
            "max_fatigue_per_day": 15,
            # Phase 2B: outdoor avoidance
            "is_outdoor_list": [False] + [getattr(poi, "is_outdoor", False) for poi in pois],
        }
        
        # If real matrix provided, extract distance and duration for this subset of locations
        if matrix:
            n = len(locations)
            distance_matrix = [[0.0]*n for _ in range(n)]
            duration_matrix = [[0.0]*n for _ in range(n)]
            
            for i in range(n):
                for j in range(n):
                    loc_i = locations[i]
                    loc_j = locations[j]
                    if (loc_i, loc_j) in matrix:
                        dist, dur = matrix[(loc_i, loc_j)]
                        distance_matrix[i][j] = dist
                        duration_matrix[i][j] = dur
                        
            problem["distance_matrix"] = distance_matrix
            problem["duration_matrix"] = duration_matrix
            
        return problem

    def solve_day(
        self,
        pois: List[POI],
        hotel: Hotel,
        day: DayPlan,
        time_limit: int = 30,
        solver_type: str = "ortools",
        matrix: Optional[Dict] = None,
    ) -> Optional[TravelItineraryDay]:
        """Solve routing for a single day (used for re-route)."""
        if not pois:
            return TravelItineraryDay(
                day_index=day.day_index, date=day.date,
                start_hotel_name=hotel.name, start_hotel_location=hotel.location,
                end_hotel_name=hotel.name, end_hotel_location=hotel.location,
                stops=[], total_travel_min=0, total_visit_min=0,
                total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                start_time_min=day.start_time_min,
                end_time_min=day.end_time_min,
            )

        problem = self.build_problem_data(pois, hotel, day, matrix)
        poi_lookup = {i + 1: pois[i] for i in range(len(pois))}

        try:
            solver = create_solver(solver_type, problem)
            solution = solver.solve(
                time_limit_seconds=time_limit,
                vehicle_penalty_weight=0,
                distance_weight=1.0,
            )
        except Exception as e:
            logger.error(f"Day {day.day_index}: Solver error: {e}")
            return None

        if not solution or solution.get("status") in ("error", "no_solution_found"):
            logger.warning(f"Day {day.day_index}: No solution found")
            return None

        routes = solution.get("routes", [])
        if not routes:
            return None

        route = routes[0]
        stops = []
        total_fee = 0.0

        for stop_data in route.get("route", []):
            loc_idx = stop_data.get("location", stop_data.get("index", 0))
            if loc_idx == 0:
                continue  # skip depot

            poi = poi_lookup.get(loc_idx)
            if not poi:
                continue

            arrival = int(stop_data.get("time", stop_data.get("arrival_time", 0)))
            stop = TravelItineraryStop(
                poi_id=poi.id,
                poi_name=poi.name,
                location=poi.location,
                arrival_time_min=arrival,
                departure_time_min=arrival + poi.visit_duration_min,
                visit_duration_min=poi.visit_duration_min,
                travel_time_from_prev_min=0,
                entrance_fee=poi.entrance_fee,
            )
            stops.append(stop)
            total_fee += poi.entrance_fee

        return TravelItineraryDay(
            day_index=day.day_index,
            date=day.date,
            start_hotel_name=hotel.name,
            start_hotel_location=hotel.location,
            end_hotel_name=hotel.name,
            end_hotel_location=hotel.location,
            stops=stops,
            total_travel_min=int(route.get("travel_time_minutes", 0)),
            total_visit_min=sum(s.visit_duration_min for s in stops),
            total_distance_km=round(route.get("distance_km", 0.0), 2),
            total_entrance_fee=total_fee,
            num_pois=len(stops),
            start_time_min=day.start_time_min,
            end_time_min=day.end_time_min,
        )

