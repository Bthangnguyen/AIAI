"""Tests for TravelPlanService orchestrator."""
import pytest
from unittest.mock import MagicMock, patch
from src.models.domain import (
    Location, TimeWindow, POI, Hotel, DayPlan,
    TravelConstraints, TransportMode,
)
from src.models.api import TravelPlanRequest
from src.models.errors import ErrorCode, SolverException
from src.services.travel_plan_service import TravelPlanService


class TestTravelPlanService:

    def test_auto_generate_day_plans(self):
        """When day_plans is None, service auto-generates them."""
        req = TravelPlanRequest(
            pois=[
                POI(id="p1", name="P1", category="test",
                    location=Location(latitude=10.77, longitude=106.70),
                    visit_duration_min=60),
            ],
            hotels=[
                Hotel(id="h1", name="H1",
                      location=Location(latitude=10.78, longitude=106.70),
                      assigned_days=[0, 1]),
            ],
            constraints=TravelConstraints(num_days=2),
            day_plans=None,
        )

        service = TravelPlanService()
        day_plans = service._generate_day_plans(req)

        assert len(day_plans) == 2
        assert day_plans[0].day_index == 0
        assert day_plans[0].hotel_id == "h1"
        assert day_plans[1].day_index == 1
        assert day_plans[1].hotel_id == "h1"

    def test_resolve_hotel_for_day(self):
        """Correctly maps hotels to days via assigned_days."""
        hotels = [
            Hotel(id="h1", name="H1",
                  location=Location(latitude=10.77, longitude=106.70),
                  assigned_days=[0]),
            Hotel(id="h2", name="H2",
                  location=Location(latitude=10.80, longitude=106.73),
                  assigned_days=[1, 2]),
        ]

        service = TravelPlanService()
        assert service._resolve_hotel(hotels, 0).id == "h1"
        assert service._resolve_hotel(hotels, 1).id == "h2"
        assert service._resolve_hotel(hotels, 2).id == "h2"
        # Fallback to first hotel for unassigned day
        assert service._resolve_hotel(hotels, 99).id == "h1"

    def test_plan_too_many_locked_pois(self):
        """Requesting too many locked POIs or exceeding time budget should raise TOO_MANY_LOCKED exception."""
        # 1. More locked POIs than total day plans max_pois
        req_too_many = TravelPlanRequest(
            pois=[
                POI(id="p1", name="P1", category="test", location=Location(latitude=10.77, longitude=106.70), visit_duration_min=60, is_locked=True),
                POI(id="p2", name="P2", category="test", location=Location(latitude=10.77, longitude=106.70), visit_duration_min=60, is_locked=True),
            ],
            hotels=[
                Hotel(id="h1", name="H1", location=Location(latitude=10.78, longitude=106.70), assigned_days=[0]),
            ],
            constraints=TravelConstraints(num_days=1),
            day_plans=[
                DayPlan(day_index=0, date="2026-06-01", hotel_id="h1", max_pois=1, max_daily_minutes=480),
            ]
        )
        service = TravelPlanService()
        with pytest.raises(SolverException) as excinfo:
            service.plan(req_too_many)
        assert excinfo.value.error_code == ErrorCode.TOO_MANY_LOCKED

        # 2. Total duration of locked POIs exceeds active time budget
        req_too_long = TravelPlanRequest(
            pois=[
                POI(id="p1", name="P1", category="test", location=Location(latitude=10.77, longitude=106.70), visit_duration_min=500, is_locked=True),
            ],
            hotels=[
                Hotel(id="h1", name="H1", location=Location(latitude=10.78, longitude=106.70), assigned_days=[0]),
            ],
            constraints=TravelConstraints(num_days=1),
            day_plans=[
                DayPlan(day_index=0, date="2026-06-01", hotel_id="h1", max_pois=5, max_daily_minutes=480),
            ]
        )
        with pytest.raises(SolverException) as excinfo:
            service.plan(req_too_long)
        assert excinfo.value.error_code == ErrorCode.TOO_MANY_LOCKED

    def test_plan_budget_exceeded(self):
        """When budget is too low to pay for locked/mandatory POIs, BUDGET_EXCEEDED is raised."""
        req = TravelPlanRequest(
            pois=[
                POI(id="p1", name="P1", category="test", location=Location(latitude=10.77, longitude=106.70), visit_duration_min=60, entrance_fee=200000, is_locked=True),
            ],
            hotels=[
                Hotel(id="h1", name="H1", location=Location(latitude=10.78, longitude=106.70), assigned_days=[0]),
            ],
            constraints=TravelConstraints(num_days=1, budget_total=100000),  # Budget is 100k, but locked entrance fee is 200k
            day_plans=[
                DayPlan(day_index=0, date="2026-06-01", hotel_id="h1", max_pois=5, max_daily_minutes=480),
            ]
        )
        service = TravelPlanService()
        # Mock OSRM build_matrix to avoid external API dependencies
        service.distance_cache.build_matrix = MagicMock(return_value={})
        
        # Mock solver to return a solved day, so we enter budget validation
        mock_day_result = MagicMock()
        mock_day_result.total_entrance_fee = 200000
        service.solver.solve_trip = MagicMock(return_value=[mock_day_result])

        with pytest.raises(SolverException) as excinfo:
            service.plan(req)
        assert excinfo.value.error_code == ErrorCode.BUDGET_EXCEEDED

    def test_plan_osrm_unreachable(self):
        """When OSRM fails and there is no cache offline, OSRM_UNREACHABLE is raised."""
        req = TravelPlanRequest(
            pois=[
                POI(id="p1", name="P1", category="test", location=Location(latitude=10.77, longitude=106.70), visit_duration_min=60),
            ],
            hotels=[
                Hotel(id="h1", name="H1", location=Location(latitude=10.78, longitude=106.70), assigned_days=[0]),
            ],
            constraints=TravelConstraints(num_days=1),
            day_plans=[
                DayPlan(day_index=0, date="2026-06-01", hotel_id="h1", max_pois=5, max_daily_minutes=480),
            ]
        )
        service = TravelPlanService()
        
        # Simulating OSRM offline with 0 cache hit rate
        service.distance_cache.build_matrix = MagicMock(return_value={})
        service.distance_cache.osrm_failed = True
        service.distance_cache.cache_hit_rate = 0.0

        with pytest.raises(SolverException) as excinfo:
            service.plan(req)
        assert excinfo.value.error_code == ErrorCode.OSRM_UNREACHABLE

