"""
OR-Tools CVRPTW Solver Implementation

Capacitated Vehicle Routing Problem with Time Windows solver
using Google OR-Tools constraint programming.
"""

import math
import time
import threading
import logging
from typing import List, Dict, Optional

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from ...utils.distance_calculator import haversine_distance
from ...utils.time_formatter import minutes_to_time, round_to_5_minutes

logger = logging.getLogger(__name__)


class ORToolsSolverImpl:
    """OR-Tools implementation of CVRPTW solver."""
    
    def __init__(self, problem_data: Dict):
        """
        Initialize OR-Tools solver with problem data.
        
        Args:
            problem_data: Dictionary containing problem definition
        """
        self.problem_data = problem_data
        self._validate_data()
        self._prepare_data()
        self._manager = None
        self._routing = None
    
    def _validate_data(self):
        """Validate input data."""
        required_keys = ['locations', 'demands', 'time_windows', 
                        'vehicle_capacities', 'num_vehicles']
        for key in required_keys:
            if key not in self.problem_data:
                raise ValueError(f"Missing required key: {key}")
        
        n_locations = len(self.problem_data['locations'])
        if len(self.problem_data['demands']) != n_locations:
            raise ValueError("Demands length must match locations length")
        if len(self.problem_data['time_windows']) != n_locations:
            raise ValueError("Time windows length must match locations length")
    
    def _prepare_data(self):
        """Prepare and compute derived data."""
        # Set defaults
        self.problem_data.setdefault('depot', 0)
        # Build depot indices set for time matrix computation
        starts = self.problem_data.get('starts')
        ends = self.problem_data.get('ends')
        if starts is not None and ends is not None:
            self._depot_indices_prep = set(starts + ends)
        else:
            self._depot_indices_prep = {self.problem_data['depot']}
        self.problem_data.setdefault('service_time', 0)
        self.problem_data.setdefault('vehicle_speed', 1.0)
        
        # Compute distance matrix (only if not provided)
        if 'distance_matrix' not in self.problem_data:
            self.problem_data['distance_matrix'] = self._compute_distance_matrix()
        
        # Compute time matrix (only if not provided)
        if 'time_matrix' not in self.problem_data:
            self.problem_data['time_matrix'] = self._compute_time_matrix()
    
    def _compute_distance_matrix(self) -> List[List[float]]:
        """Compute distance matrix between all locations."""
        locations = self.problem_data['locations']
        n = len(locations)
        distance_matrix = [[0.0] * n for _ in range(n)]
        
        use_latlon = (
            self.problem_data.get('coord_type', '').lower() == 'latlon' 
            if isinstance(self.problem_data.get('coord_type', ''), str) 
            else bool(self.problem_data.get('use_haversine', False))
        )
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    distance_matrix[i][j] = 0.0
                    continue
                
                loc1 = locations[i]
                loc2 = locations[j]
                
                if use_latlon:
                    distance = haversine_distance(loc1, loc2)
                else:
                    # Euclidean distance
                    try:
                        distance = math.sqrt((loc2[0] - loc1[0])**2 + (loc2[1] - loc1[1])**2)
                    except Exception:
                        distance = 0.0
                
                distance_matrix[i][j] = distance
        
        return distance_matrix
    
    def _compute_time_matrix(self) -> List[List[int]]:
        """
        Compute time matrix (travel time + service time).
        
        Service time is calculated dynamically as:
        - Depot: 0 minutes
        - Customer: 10 minutes (fixed) + 2 minutes per unit
        """
        distance_matrix = self.problem_data['distance_matrix']
        demands = self.problem_data['demands']
        depot_set = self._depot_indices_prep
        n = len(distance_matrix)
        
        time_matrix = [[0] * n for _ in range(n)]
        
        # If duration_matrix is provided (Travel Domain via OSRM)
        if 'duration_matrix' in self.problem_data:
            duration_matrix = self.problem_data['duration_matrix']
            for i in range(n):
                for j in range(n):
                    travel_time = int(duration_matrix[i][j] * 100)
                    # IMPORTANT ASSUMPTION (Travel Domain):
                    # demands[j] = visit_duration_min (POI visit time).
                    # This value serves DUAL purpose:
                    #   1) Capacity dimension: sum(demands) <= max_daily_minutes (visit-time budget)
                    #   2) Time dimension: time_matrix[i][j] = travel_time + visit_time
                    # The capacity constraint is STRICTER because it ignores travel_time.
                    # This is acceptable: if visit-time alone exceeds the budget, no route is valid.
                    # If travel_time pushes total over budget, the time dimension catches it.
                    service_time_scaled = int(demands[j] * 100) if j not in depot_set else 0
                    time_matrix[i][j] = travel_time + service_time_scaled
            return time_matrix
            
        # Fallback path when OSRM duration_matrix is not available (using haversine speed estimates)
        speed = self.problem_data.get('vehicle_speed', 40.0)
        for i in range(n):
            for j in range(n):
                # distance is in km, speed in km/h. travel_time in hours -> minutes -> scaled
                travel_time_hours = distance_matrix[i][j] / speed
                travel_time_scaled = int(travel_time_hours * 60 * 100)
                
                # In Travel Domain, demands[j] = visit_duration_min
                service_time_scaled = int(demands[j] * 100) if j not in depot_set else 0
                
                time_matrix[i][j] = travel_time_scaled + service_time_scaled
        
        return time_matrix
    
    def _create_distance_callback(self, manager):
        """Create callback to get distance between nodes."""
        distance_matrix = self.problem_data['distance_matrix']
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 100)  # Scale for precision
        
        return distance_callback
    
    def _create_demand_callback(self, manager):
        """Create callback to get demand at each node."""
        demands = self.problem_data['demands']
        
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]
        
        return demand_callback
    
    def _create_time_callback(self, manager):
        """Create callback to get time between nodes."""
        time_matrix = self.problem_data['time_matrix']
        
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]
        
        return time_callback
    
    def solve(
        self,
        time_limit_seconds: int = 120,
        log_search: bool = False,
        vehicle_penalty_weight: float = 100000.0,
        distance_weight: float = 1.0,
        **kwargs
    ) -> Optional[Dict]:
        """
        Solve CVRPTW problem using OR-Tools.
        
        Supports both single-depot and multi-depot modes.
        Multi-depot mode is activated when 'starts' and 'ends' arrays
        are present in problem_data.
        
        Args:
            time_limit_seconds: Maximum time for solver
            log_search: Whether to log search progress
            vehicle_penalty_weight: Weight for minimizing number of vehicles (single-depot only)
            distance_weight: Weight for distance minimization
            **kwargs: diversity_penalty, rhythm_penalty, drop_penalty, first_solution_strategy
        """
        N = len(self.problem_data['distance_matrix'])
        num_vehicles = self.problem_data['num_vehicles']
        
        # === Multi-depot vs Single-depot ===
        starts = self.problem_data.get('starts')
        ends = self.problem_data.get('ends')
        is_multi_depot = starts is not None and ends is not None
        
        if is_multi_depot:
            manager = pywrapcp.RoutingIndexManager(N, num_vehicles, starts, ends)
            depot_indices = set(starts + ends)
            logger.info(
                f"Preparing OR-Tools MULTI-DEPOT model: nodes={N}, "
                f"vehicles={num_vehicles}, starts={starts}, ends={ends}"
            )
        else:
            depot = self.problem_data.get('depot', 0)
            manager = pywrapcp.RoutingIndexManager(N, num_vehicles, depot)
            depot_indices = {depot}
            logger.info(
                f"Preparing OR-Tools model: nodes={N}, "
                f"vehicles={num_vehicles}, depot={depot}"
            )
        
        # Store for extraction
        self._depot_indices = depot_indices
        self._is_multi_depot = is_multi_depot
        
        routing = pywrapcp.RoutingModel(manager)
        
        # === Distance callback with diversity/rhythm penalties ===
        diversity_penalty = kwargs.get('diversity_penalty', 50000)
        rhythm_penalty = kwargs.get('rhythm_penalty', 30000)
        categories = self.problem_data.get('categories', [])
        intensities = self.problem_data.get('intensities', [])
        distance_matrix = self.problem_data['distance_matrix']
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            base_cost = int(distance_matrix[from_node][to_node] * 100)
            
            # Apply penalties only between non-depot nodes
            if from_node not in depot_indices and to_node not in depot_indices:
                if (categories
                    and from_node < len(categories) and to_node < len(categories)
                    and categories[from_node] and categories[to_node]
                    and categories[from_node] == categories[to_node]):
                    base_cost += diversity_penalty
                
                if (intensities
                    and from_node < len(intensities) and to_node < len(intensities)
                    and intensities[from_node] == "heavy"
                    and intensities[to_node] == "heavy"):
                    base_cost += rhythm_penalty
            
            return base_cost
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        
        if distance_weight != 1.0:
            def weighted_distance_callback(from_index, to_index):
                return int(distance_callback(from_index, to_index) * distance_weight)
            weighted_idx = routing.RegisterTransitCallback(weighted_distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(weighted_idx)
        else:
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # === Capacity constraint ===
        demand_callback = self._create_demand_callback(manager)
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0,
            self.problem_data['vehicle_capacities'],
            True, 'Capacity'
        )
        
        # === Time dimension ===
        time_callback = self._create_time_callback(manager)
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        vehicle_time_windows = self.problem_data.get('vehicle_time_windows')
        if vehicle_time_windows:
            max_time = int(max(tw[1] for tw in vehicle_time_windows) * 100)
        else:
            max_time = int(max(tw[1] for tw in self.problem_data['time_windows']) * 100)
        
        routing.AddDimension(
            time_callback_index,
            max_time,   # allow waiting
            max_time,   # max time per vehicle
            False, 'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # POI time windows
        for loc_idx, tw in enumerate(self.problem_data['time_windows']):
            if loc_idx in depot_indices:
                continue
            index = manager.NodeToIndex(loc_idx)
            time_dimension.CumulVar(index).SetRange(int(tw[0] * 100), int(tw[1] * 100))
        
        # Per-vehicle start/end time windows
        if vehicle_time_windows:
            for vid in range(num_vehicles):
                vtw = vehicle_time_windows[vid]
                time_dimension.CumulVar(routing.Start(vid)).SetRange(
                    int(vtw[0] * 100), int(vtw[1] * 100)
                )
                time_dimension.CumulVar(routing.End(vid)).SetRange(
                    int(vtw[0] * 100), int(vtw[1] * 100)
                )
        else:
            # Single depot time window for all vehicles
            depot_tw = self.problem_data['time_windows'][self.problem_data.get('depot', 0)]
            for vid in range(num_vehicles):
                time_dimension.CumulVar(routing.Start(vid)).SetRange(
                    int(depot_tw[0] * 100), int(depot_tw[1] * 100)
                )
        
        # === Vehicle penalty (single-depot only) ===
        if not is_multi_depot:
            routing.SetFixedCostOfAllVehicles(int(vehicle_penalty_weight))
        
        logger.info(
            f"Penalties: diversity={diversity_penalty}, rhythm={rhythm_penalty}, "
            f"multi_depot={is_multi_depot}"
        )
        
        # === Disjunction & Meal constraints ===
        drop_penalty = kwargs.get('drop_penalty', 10_000_000_000)
        is_locked_list = self.problem_data.get('is_locked_list', [])
        meal_assignments = self.problem_data.get('meal_assignments', {})
        
        for node in range(N):
            if node in depot_indices:
                continue
            
            index = manager.NodeToIndex(node)
            
            if node in meal_assignments:
                # Meal POI: lock to specific vehicle (day), must visit
                vehicle_id = meal_assignments[node]
                routing.solver().Add(routing.VehicleVar(index) == vehicle_id)
                logger.info(f"Node {node} is meal -> locked to vehicle {vehicle_id}")
            elif is_locked_list and node < len(is_locked_list) and is_locked_list[node]:
                # Locked POI: must visit (no disjunction)
                logger.info(f"Node {node} is locked -> must visit")
            else:
                # Regular POI: can be dropped with high penalty
                routing.AddDisjunction([index], drop_penalty)
        
        # === Search parameters ===
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        strategy_name = kwargs.get('first_solution_strategy', 'PATH_CHEAPEST_ARC')
        search_parameters.first_solution_strategy = getattr(
            routing_enums_pb2.FirstSolutionStrategy, strategy_name
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = time_limit_seconds
        search_parameters.log_search = log_search
        
        # === Monitor thread ===
        solving = [True]
        start_time = time.time()
        
        def monitor_progress():
            last_report = start_time
            while solving[0]:
                time.sleep(1)
                now = time.time()
                if now - last_report >= 5.0:
                    last_report = now
                    logger.info(f"[{now - start_time:.0f}s] OR-Tools optimizing...")
        
        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()
        
        logger.info(f"Starting OR-Tools solver (time_limit={time_limit_seconds}s, nodes={N}, vehicles={num_vehicles})...")
        solution = routing.SolveWithParameters(search_parameters)
        
        solving[0] = False
        monitor_thread.join(timeout=1.0)
        
        if solution:
            logger.info(f"✓ Solution found - Objective: {solution.ObjectiveValue():,.0f}")
            return self._extract_solution(manager, routing, solution)
        else:
            logger.warning("No solution found")
            return None
    
    def _extract_solution(self, manager, routing, solution) -> Dict:
        """Extract solution details from OR-Tools solution."""
        total_distance = 0
        total_load = 0
        routes = []
        num_vehicles_used = 0
        
        capacity_dimension = routing.GetDimensionOrDie('Capacity')
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for vehicle_id in range(self.problem_data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            is_first_arc = not self._is_multi_depot
            segment_distances = []
            
            # First pass: collect all stops to calculate total load
            temp_route = []
            temp_index = index
            while not routing.IsEnd(temp_index):
                node_index = manager.IndexToNode(temp_index)
                demand = (
                    self.problem_data['demands'][node_index] 
                    if node_index < len(self.problem_data['demands']) 
                    else 0
                )
                temp_route.append((node_index, demand))
                temp_index = solution.Value(routing.NextVar(temp_index))
            
            # Calculate total load
            total_route_load = sum(d for _, d in temp_route)
            
            # Second pass: build route with delivery model
            current_load = total_route_load
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                time_minutes = solution.Value(time_var) / 100.0
                
                demand = (
                    self.problem_data['demands'][node_index] 
                    if node_index < len(self.problem_data['demands']) 
                    else 0
                )
                
                time_window = self.problem_data['time_windows'][node_index]
                time_window_start = time_window[0]
                time_window_end = time_window[1]
                
                # Delivery model: load decreases after delivery
                if node_index in self._depot_indices:
                    load_before = 0
                    load_after = total_route_load
                else:
                    load_before = current_load
                    load_after = current_load - demand
                    current_load = load_after
                
                time_rounded = round_to_5_minutes(time_minutes)
                
                route.append({
                    'location': node_index,
                    'load_before': load_before,
                    'load_after': load_after,
                    'time': time_rounded,
                    'time_formatted': minutes_to_time(time_minutes),
                    'time_window': time_window,
                    'time_window_formatted': (
                        f"{minutes_to_time(time_window_start)} - "
                        f"{minutes_to_time(time_window_end)}"
                    ),
                    'segment_distance': 0.0,
                    'segment_distance_formatted': "0.00 km"
                })
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                arc_cost = routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
                
                # Subtract fixed cost from first arc
                if is_first_arc:
                    fixed_cost_scaled = int(routing.GetFixedCostOfVehicle(vehicle_id))
                    arc_cost -= fixed_cost_scaled
                    is_first_arc = False
                
                route_distance += arc_cost
                segment_distances.append(arc_cost)
            
            # Add final depot stop
            node_index = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            time_minutes = solution.Value(time_var) / 100.0
            time_rounded = round_to_5_minutes(time_minutes)
            time_window = self.problem_data['time_windows'][node_index]
            
            route.append({
                'location': node_index,
                'load_before': current_load,
                'load_after': 0,
                'time': time_rounded,
                'time_formatted': minutes_to_time(time_minutes),
                'time_window': time_window,
                'time_window_formatted': (
                    f"{minutes_to_time(time_window[0])} - "
                    f"{minutes_to_time(time_window[1])}"
                ),
                'segment_distance': 0.0,
                'segment_distance_formatted': "0.00 km"
            })
            
            # Update segment distances
            for i in range(1, len(route)):
                if i - 1 < len(segment_distances):
                    distance_km = segment_distances[i - 1] / 100.0
                    route[i]['segment_distance'] = round(distance_km, 2)
                    route[i]['segment_distance_formatted'] = f"{distance_km:.2f} km"
            
            # Build timeline segments
            segments = self._build_timeline_segments(route, segment_distances)
            
            # Only count routes with customers
            if len(route) > 2:
                num_vehicles_used += 1
                route_distance = route_distance / 100.0
                route_load = total_route_load
                
                vehicle_capacity = self.problem_data['vehicle_capacities'][vehicle_id]
                saturation = (
                    (route_load / vehicle_capacity * 100) 
                    if vehicle_capacity > 0 
                    else 0
                )
                
                route_start_time = route[0]['time']
                route_end_time = route[-1]['time']
                route_duration_minutes = route_end_time - route_start_time
                
                # Calculate service time
                service_time_minutes = 0
                num_customers = 0
                for stop in route:
                    if stop['location'] not in self._depot_indices:
                        num_customers += 1
                        units_delivered = stop['load_before'] - stop['load_after']
                        service_time_minutes += 10 + (2 * units_delivered)
                
                service_time_minutes = round_to_5_minutes(service_time_minutes)
                travel_time_minutes = max(0, route_duration_minutes - service_time_minutes)
                
                routes.append({
                    'vehicle_id': vehicle_id,
                    'route': route,
                    'segments': segments,
                    'distance': route_distance,
                    'distance_km': route_distance,
                    'distance_formatted': f"{route_distance:.2f} km",
                    'load': route_load,
                    'load_units': route_load,
                    'load_formatted': f"{route_load} units",
                    'capacity': vehicle_capacity,
                    'saturation_pct': saturation,
                    'duration_minutes': route_duration_minutes,
                    'duration_formatted': (
                        f"{int(route_duration_minutes // 60)}h "
                        f"{int(route_duration_minutes % 60)}m"
                    ),
                    'duration_hours': round(route_duration_minutes / 60.0, 2),
                    'travel_time_minutes': travel_time_minutes,
                    'travel_time_hours': travel_time_minutes / 60.0,
                    'travel_time_formatted': (
                        f"{int(travel_time_minutes // 60)}h "
                        f"{int(travel_time_minutes % 60)}m"
                    ),
                    'service_time_minutes': service_time_minutes,
                    'service_time_hours': service_time_minutes / 60.0,
                    'service_time_formatted': (
                        f"{int(service_time_minutes // 60)}h "
                        f"{int(service_time_minutes % 60)}m"
                    ),
                    'num_customers': num_customers
                })
                
                total_distance += route_distance
                total_load += route_load
        
        # Calculate overall metrics
        return self._build_solution_summary(
            routes, num_vehicles_used, total_distance, total_load,
            solution.ObjectiveValue() / 100.0
        )
    
    def _build_timeline_segments(
        self, 
        route: List[Dict], 
        segment_distances: List[float]
    ) -> List[Dict]:
        """Build timeline segments for route visualization."""
        segments = []
        
        for i in range(len(route) - 1):
            from_stop = route[i]
            to_stop = route[i + 1]
            
            segment_distance_km = 0.0
            if i < len(segment_distances):
                segment_distance_km = segment_distances[i] / 100.0
            
            time_diff = to_stop['time'] - from_stop['time']
            
            if to_stop['location'] not in self._depot_indices:
                # Going to customer
                units_delivered = to_stop['load_before'] - to_stop['load_after']
                service_time_minutes = 10 + (2 * units_delivered)
                travel_time_minutes = max(0, time_diff - service_time_minutes)
                
                segments.append({
                    'type': 'travel',
                    'from_location': from_stop['location'],
                    'to_location': to_stop['location'],
                    'start_time': from_stop['time'],
                    'end_time': from_stop['time'] + travel_time_minutes,
                    'duration_minutes': travel_time_minutes,
                    'distance_km': round(segment_distance_km, 2)
                })
                
                segments.append({
                    'type': 'service',
                    'location': to_stop['location'],
                    'start_time': from_stop['time'] + travel_time_minutes,
                    'end_time': to_stop['time'],
                    'duration_minutes': service_time_minutes,
                    'units': units_delivered
                })
            else:
                # Returning to depot
                segments.append({
                    'type': 'travel',
                    'from_location': from_stop['location'],
                    'to_location': to_stop['location'],
                    'start_time': from_stop['time'],
                    'end_time': to_stop['time'],
                    'duration_minutes': time_diff,
                    'distance_km': round(segment_distance_km, 2)
                })
        
        return segments
    
    def _build_solution_summary(
        self,
        routes: List[Dict],
        num_vehicles_used: int,
        total_distance: float,
        total_load: int,
        objective_value: float
    ) -> Dict:
        """Build comprehensive solution summary."""
        total_capacity = sum(r['capacity'] for r in routes) if routes else 0
        avg_saturation = (
            (total_load / total_capacity * 100) 
            if total_capacity > 0 
            else 0
        )
        
        total_trips = len(routes)
        avg_trips_per_vehicle = (
            total_trips / num_vehicles_used 
            if num_vehicles_used > 0 
            else 0
        )
        avg_distance_per_vehicle = (
            total_distance / num_vehicles_used 
            if num_vehicles_used > 0 
            else 0
        )
        
        total_duration_minutes = sum(r['duration_minutes'] for r in routes)
        total_travel_time_minutes = sum(r['travel_time_minutes'] for r in routes)
        total_service_time_minutes = sum(r['service_time_minutes'] for r in routes)
        
        avg_duration_per_vehicle_minutes = (
            total_duration_minutes / num_vehicles_used 
            if num_vehicles_used > 0 
            else 0
        )
        avg_travel_time_per_vehicle_minutes = (
            total_travel_time_minutes / num_vehicles_used 
            if num_vehicles_used > 0 
            else 0
        )
        avg_service_time_per_vehicle_minutes = (
            total_service_time_minutes / num_vehicles_used 
            if num_vehicles_used > 0 
            else 0
        )
        
        # Count customers served and dropped
        served_customers = set()
        for route in routes:
            for stop in route['route']:
                if stop['location'] not in self._depot_indices:
                    served_customers.add(stop['location'])
        
        customers_served = len(served_customers)
        num_depots = len(self._depot_indices)
        customers_total = len(self.problem_data['demands']) - num_depots
        
        dropped_customers = []
        for i in range(len(self.problem_data['demands'])):
            if i not in self._depot_indices and i not in served_customers:
                dropped_customers.append({'index': i})
        
        # Log summary
        logger.info(f"  Vehicles used: {num_vehicles_used}/{self.problem_data['num_vehicles']}")
        logger.info(f"  Total trips: {total_trips}")
        logger.info(f"  Average trips per vehicle: {avg_trips_per_vehicle:.1f}")
        logger.info(f"  Total distance: {total_distance:.2f} km")
        logger.info(f"  Average distance per vehicle: {avg_distance_per_vehicle:.2f} km")
        logger.info(
            f"  Total load: {total_load}/{total_capacity} units "
            f"({avg_saturation:.1f}% saturation)"
        )
        logger.info(
            f"  Average travel time per vehicle: {avg_travel_time_per_vehicle_minutes:.0f} min "
            f"(excluding service)"
        )
        logger.info(
            f"  Average total time per vehicle: {avg_duration_per_vehicle_minutes:.0f} min "
            f"(including service)"
        )
        logger.info(f"  Customers served: {customers_served}/{customers_total}")
        
        return {
            'status': 'success',
            'num_vehicles_used': num_vehicles_used,
            'total_vehicles_available': self.problem_data['num_vehicles'],
            'total_trips': total_trips,
            'avg_trips_per_vehicle': round(avg_trips_per_vehicle, 2),
            'total_distance': total_distance,
            'total_distance_km': round(total_distance, 2),
            'total_distance_formatted': f"{total_distance:.2f} km",
            'avg_distance_per_vehicle_km': round(avg_distance_per_vehicle, 2),
            'avg_distance_per_vehicle_formatted': f"{avg_distance_per_vehicle:.2f} km",
            'total_load': total_load,
            'average_saturation_pct': round(avg_saturation, 1),
            'total_duration_minutes': round(total_duration_minutes, 1),
            'total_duration_hours': round(total_duration_minutes / 60.0, 2),
            'total_duration_formatted': (
                f"{int(total_duration_minutes // 60)}h "
                f"{int(total_duration_minutes % 60)}m"
            ),
            'total_travel_time_minutes': round(total_travel_time_minutes, 1),
            'total_travel_time_hours': round(total_travel_time_minutes / 60.0, 2),
            'total_travel_time_formatted': (
                f"{int(total_travel_time_minutes // 60)}h "
                f"{int(total_travel_time_minutes % 60)}m"
            ),
            'total_service_time_minutes': round(total_service_time_minutes, 1),
            'total_service_time_hours': round(total_service_time_minutes / 60.0, 2),
            'total_service_time_formatted': (
                f"{int(total_service_time_minutes // 60)}h "
                f"{int(total_service_time_minutes % 60)}m"
            ),
            'avg_duration_per_vehicle_minutes': round(avg_duration_per_vehicle_minutes, 1),
            'avg_duration_per_vehicle_hours': round(avg_duration_per_vehicle_minutes / 60.0, 2),
            'avg_duration_per_vehicle_formatted': (
                f"{int(avg_duration_per_vehicle_minutes // 60)}h "
                f"{int(avg_duration_per_vehicle_minutes % 60)}m"
            ),
            'avg_travel_time_per_vehicle_minutes': round(avg_travel_time_per_vehicle_minutes, 1),
            'avg_travel_time_per_vehicle_hours': round(avg_travel_time_per_vehicle_minutes / 60.0, 2),
            'avg_travel_time_per_vehicle_formatted': (
                f"{int(avg_travel_time_per_vehicle_minutes // 60)}h "
                f"{int(avg_travel_time_per_vehicle_minutes % 60)}m"
            ),
            'avg_service_time_per_vehicle_minutes': round(avg_service_time_per_vehicle_minutes, 1),
            'avg_service_time_per_vehicle_hours': round(avg_service_time_per_vehicle_minutes / 60.0, 2),
            'avg_service_time_per_vehicle_formatted': (
                f"{int(avg_service_time_per_vehicle_minutes // 60)}h "
                f"{int(avg_service_time_per_vehicle_minutes % 60)}m"
            ),
            'routes': routes,
            'customers_served': customers_served,
            'customers_total': customers_total,
            'dropped_customers': dropped_customers,
            'objective_value': objective_value
        }
