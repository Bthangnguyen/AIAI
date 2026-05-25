import pytest
from src.core.solvers.ortools_solver import ORToolsSolver

def test_is_locked_poi_prevents_drop():
    """Test that a locked POI is not dropped, even if it forces other POIs to be dropped or fails the time window."""
    
    # Depot (0), POI_1 (1), POI_2 (locked, 2)
    # We set tight time windows so they can't both be visited.
    # POI_1 takes 60 mins. POI_2 takes 60 mins.
    # Total time available: 100 mins.
    # POI_1 is closer, so without locked, solver would visit POI_1 and drop POI_2.
    # But since POI_2 is locked, the solver MUST visit POI_2, and therefore will drop POI_1.
    
    problem_data = {
        "locations": [(0, 0), (0, 1), (0, 5)],  # Depot, POI_1 (closer), POI_2 (farther)
        "demands": [0, 60, 60],
        "time_windows": [
            (0, 100),  # Depot max time 100 mins
            (0, 100),  # POI_1
            (0, 100),  # POI_2
        ],
        "vehicle_capacities": [100],  # Max 100 mins daily
        "num_vehicles": 1,
        "depot": 0,
        "service_time": 0,
        "coord_type": "latlon",
        # Distance matrix (in km)
        "distance_matrix": [
            [0.0, 1.0, 5.0],
            [1.0, 0.0, 4.0],
            [5.0, 4.0, 0.0],
        ],
        # Time matrix (in minutes) - let's say it takes 10 mins to POI_1, 50 mins to POI_2
        "time_matrix": [
            [0, 10, 50],
            [10, 0, 40],
            [50, 40, 0],
        ],
        "is_locked_list": [True, False, True]  # Depot locked, POI_1 not locked, POI_2 locked
    }
    
    solver = ORToolsSolver(problem_data)
    solution = solver.solve(time_limit_seconds=5)
    
    # We expect POI_2 (index 2) to be in the route, and POI_1 (index 1) to be in dropped_customers
    assert solution is not None, "Solver should find a solution"

    
    dropped = [d['index'] for d in solution.get('dropped_customers', [])]
    
    # POI_1 (index 1) must be dropped
    assert 1 in dropped, "POI_1 should be dropped because POI_2 is locked and takes priority"
    
    # POI_2 (index 2) MUST NOT be dropped
    assert 2 not in dropped, "POI_2 is locked and must not be dropped"

