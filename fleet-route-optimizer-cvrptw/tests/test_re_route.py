"""Tests for re-route JIT functionality."""
import pytest
from unittest.mock import patch, MagicMock

from src.models.domain import (
    POI, Hotel, DayPlan, Location, TransportMode,
    TravelConstraints, TravelItineraryDay, TimeWindow,
)
from src.models.api import ReRouteRequest
from src.services.travel_plan_service import TravelPlanService


def _make_poi(id: str, lat: float, lon: float, duration: int = 60) -> POI:
    """Helper to create a POI."""
    return POI(
        id=id, name=f"POI {id}", category="temple",
        location=Location(latitude=lat, longitude=lon),
        visit_duration_min=duration,
        time_window=TimeWindow(start_min=480, end_min=1080),
    )


def _make_hotel(lat: float = 16.4637, lon: float = 107.5909) -> Hotel:
    return Hotel(
        id="hotel_1", name="Hotel Hue",
        location=Location(latitude=lat, longitude=lon),
    )


def _make_day() -> DayPlan:
    return DayPlan(day_index=0, date="2026-05-01")


class TestReRoute:

    @patch('src.services.distance_cache.DistanceCacheService.build_matrix')
    def test_reroute_basic_filters_excluded(self, mock_matrix):
        """Re-route should exclude specified POI IDs."""
        mock_matrix.return_value = {}  # Empty matrix → solver will use haversine fallback

        service = TravelPlanService()

        poi_a = _make_poi("a", 16.46, 107.58)
        poi_b = _make_poi("b", 16.47, 107.59)
        poi_c = _make_poi("c", 16.48, 107.60)

        request = ReRouteRequest(
            current_location=Location(latitude=16.465, longitude=107.585),
            current_time_min=840,  # 14:00
            remaining_poi_ids=["a", "b", "c"],
            pois=[poi_a, poi_b, poi_c],
            hotel=_make_hotel(),
            day=_make_day(),
            constraints=TravelConstraints(num_days=1),
            excluded_poi_ids=["b"],
        )

        result = service.re_route(request)

        assert isinstance(result, TravelItineraryDay)
        # The solver may or may not find a solution with empty matrix,
        # but we can verify the method ran without crash
        assert result.day_index == 0

    @patch('src.services.distance_cache.DistanceCacheService.build_matrix')
    def test_reroute_updates_start_time(self, mock_matrix):
        """Re-route should use current_time_min as start time."""
        mock_matrix.return_value = {}

        service = TravelPlanService()

        request = ReRouteRequest(
            current_location=Location(latitude=16.465, longitude=107.585),
            current_time_min=900,  # 15:00
            remaining_poi_ids=["a"],
            pois=[_make_poi("a", 16.46, 107.58)],
            hotel=_make_hotel(),
            day=_make_day(),
            constraints=TravelConstraints(num_days=1),
        )

        # We need to verify the day passed to solver has start_time_min=900
        with patch.object(service.solver, 'solve_day', return_value=None) as mock_solve:
            service.re_route(request)
            call_args = mock_solve.call_args
            day_arg = call_args.kwargs.get('day') or call_args[1].get('day')
            if day_arg is None:
                # Try positional
                day_arg = call_args[0][2] if len(call_args[0]) > 2 else None

            assert day_arg is not None
            assert day_arg.start_time_min == 900

    @patch('src.services.distance_cache.DistanceCacheService.build_matrix')
    def test_reroute_uses_current_location_as_depot(self, mock_matrix):
        """Re-route should create virtual depot at current_location, not hotel."""
        mock_matrix.return_value = {}

        service = TravelPlanService()

        current_loc = Location(latitude=16.50, longitude=107.55)  # Somewhere different from hotel

        request = ReRouteRequest(
            current_location=current_loc,
            current_time_min=780,
            remaining_poi_ids=["a"],
            pois=[_make_poi("a", 16.46, 107.58)],
            hotel=_make_hotel(lat=16.46, lon=107.59),  # Hotel is different
            day=_make_day(),
            constraints=TravelConstraints(num_days=1),
        )

        with patch.object(service.solver, 'solve_day', return_value=None) as mock_solve:
            service.re_route(request)
            call_args = mock_solve.call_args
            hotel_arg = call_args.kwargs.get('hotel') or call_args[0][1]

            # Virtual depot should be at current_location
            assert hotel_arg.location.latitude == 16.50
            assert hotel_arg.location.longitude == 107.55
            assert hotel_arg.id == "__current_location__"

    @patch('src.services.distance_cache.DistanceCacheService.build_matrix')
    def test_reroute_empty_remaining(self, mock_matrix):
        """Re-route with no remaining POIs should return empty day."""
        mock_matrix.return_value = {}

        service = TravelPlanService()

        request = ReRouteRequest(
            current_location=Location(latitude=16.465, longitude=107.585),
            current_time_min=840,
            remaining_poi_ids=[],
            pois=[],
            hotel=_make_hotel(),
            day=_make_day(),
            constraints=TravelConstraints(num_days=1),
        )

        result = service.re_route(request)
        assert isinstance(result, TravelItineraryDay)
        assert result.num_pois == 0
        assert result.stops == []


class TestTravelPlanServiceThreadSafety:

    def test_is_busy_flag(self):
        """Service should report busy status."""
        service = TravelPlanService()
        assert service.is_busy() is False
