"""Tests for ORTools implementation with actual OSRM duration matrix."""
import pytest
from src.core.solvers.ortools_impl import ORToolsSolverImpl


class TestORToolsImpl:
    
    def test_uses_provided_duration_matrix(self):
        """Should use duration_matrix + demands as service time if provided."""
        problem_data = {
            "locations": [(10.0, 106.0), (10.1, 106.1)],
            "demands": [0, 60],  # Depot = 0, POI = 60 min visit
            "vehicle_capacities": [600],
            "num_vehicles": 1,
            "depot": 0,
            "duration_matrix": [[0, 30.5], [30.5, 0]],  # OSRM actual durations
            "distance_matrix": [[0, 15.0], [15.0, 0]],
            "time_windows": [(0, 1000), (0, 1000)],
        }
        
        solver = ORToolsSolverImpl(problem_data)
        time_matrix = solver._compute_time_matrix()
        
        # 30.5 min travel + 60 min visit = 90.5 min -> 9050 scaled
        assert time_matrix[0][1] == 9050
        # 30.5 min travel + 0 min visit (depot) = 30.5 min -> 3050 scaled
        assert time_matrix[1][0] == 3050
