"""Travel Solver Adapter — Stage 2 of Two-Stage solver.

Converts travel domain models (POI, Hotel, DayPlan) into the
ProblemData format that ORToolsSolverImpl expects, then runs the solver
and converts the solution back to TravelItineraryDay.
"""

from typing import List, Dict, Optional
from ..models.domain import (
    POI, Hotel, DayPlan, Location,
    TravelItineraryStop, TravelItineraryDay,
)
from ..core.solvers import create_solver
from ..config import get_logger

logger = get_logger(__name__)


class TravelSolverAdapter:
    """Adapts travel models to CVRPTW solver input and interprets output."""

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
        """Solve routing for a single day.

        Args:
            pois: POIs assigned to this day
            hotel: Hotel (depot) for this day
            day: DayPlan with constraints
            time_limit: Solver time limit in seconds
            solver_type: Solver to use
            matrix: Optional pre-calculated distance/duration matrix

        Returns:
            TravelItineraryDay or None if no solution
        """
        if not pois:
            return TravelItineraryDay(
                day_index=day.day_index, date=day.date,
                hotel_name=hotel.name, hotel_location=hotel.location,
                stops=[], total_travel_min=0, total_visit_min=0,
                total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
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

        # Extract the single route (we have 1 vehicle)
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
            hotel_name=hotel.name,
            hotel_location=hotel.location,
            stops=stops,
            total_travel_min=int(route.get("travel_time_minutes", 0)),
            total_visit_min=sum(s.visit_duration_min for s in stops),
            total_distance_km=round(route.get("distance_km", 0.0), 2),
            total_entrance_fee=total_fee,
            num_pois=len(stops),
        )
