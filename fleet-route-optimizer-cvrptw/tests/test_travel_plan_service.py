"""Tests for TravelPlanService orchestrator."""
import pytest
from src.models.domain import (
    Location, TimeWindow, POI, Hotel, DayPlan,
    TravelConstraints, TransportMode,
)
from src.models.api import TravelPlanRequest
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
