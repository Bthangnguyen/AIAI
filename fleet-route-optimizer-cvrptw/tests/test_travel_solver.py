"""Tests for Travel Solver Adapter (Stage 2)."""
import pytest
from src.models.domain import Location, TimeWindow, POI, Hotel, DayPlan
from src.services.travel_solver import TravelSolverAdapter


class TestTravelSolverAdapter:
    """Test the adapter that converts travel data to CVRPTW format."""

    def _make_poi(self, id, lat, lon, duration=60, fee=0.0, tw_start=480, tw_end=1260):
        return POI(
            id=id, name=f"POI {id}", category="test",
            location=Location(latitude=lat, longitude=lon),
            visit_duration_min=duration, entrance_fee=fee,
            priority_score=0.5,
            time_window=TimeWindow(start_min=tw_start, end_min=tw_end),
        )

    def test_build_problem_data(self):
        """Adapter correctly maps travel models to solver ProblemData format."""
        pois = [
            self._make_poi("p1", 10.77, 106.70, duration=60),
            self._make_poi("p2", 10.78, 106.71, duration=90),
        ]
        hotel = Hotel(
            id="h1", name="Hotel",
            location=Location(latitude=10.76, longitude=106.69),
        )
        day = DayPlan(
            day_index=0, date="2025-06-15", hotel_id="h1",
            max_daily_minutes=600, start_time_min=480, end_time_min=1260,
        )

        adapter = TravelSolverAdapter()
        problem = adapter.build_problem_data(pois, hotel, day)

        # Locations: hotel (depot=0), then POIs
        assert len(problem["locations"]) == 3
        assert problem["locations"][0] == (10.76, 106.69)
        assert problem["depot"] == 0
        assert problem["num_vehicles"] == 1

        # Demands = visit_duration_min (capacity model)
        assert problem["demands"] == [0, 60, 90]

        # Vehicle capacity = max_daily_minutes
        assert problem["vehicle_capacities"] == [600]

        # Time windows
        assert problem["time_windows"][0] == (480, 1260)
        assert problem["time_windows"][1] == (480, 1260)
        assert problem["time_windows"][2] == (480, 1260)

    def test_build_problem_coord_type(self):
        pois = [self._make_poi("p1", 10.77, 106.70)]
        hotel = Hotel(id="h1", name="H", location=Location(latitude=10.76, longitude=106.69))
        day = DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")

        adapter = TravelSolverAdapter()
        problem = adapter.build_problem_data(pois, hotel, day)

        assert problem["coord_type"] == "latlon"
        assert problem["service_time"] == 0

    def test_build_empty_pois(self):
        hotel = Hotel(id="h1", name="H", location=Location(latitude=10.76, longitude=106.69))
        day = DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")

        adapter = TravelSolverAdapter()
        problem = adapter.build_problem_data([], hotel, day)

        assert len(problem["locations"]) == 1  # depot only
        assert problem["demands"] == [0]
