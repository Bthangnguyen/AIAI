"""Tests for travel API request/response models."""
import pytest
from src.models.domain import (
    Location, TimeWindow, POI, Hotel, DayPlan,
    TravelConstraints, TransportMode,
)
from src.models.api import TravelPlanRequest


class TestTravelPlanRequest:
    """Test the API request model for travel planning."""

    def test_minimal_request(self):
        req = TravelPlanRequest(
            pois=[
                POI(
                    id="poi_001",
                    name="Bến Thành",
                    category="market",
                    location=Location(latitude=10.7721, longitude=106.6980),
                    visit_duration_min=60,
                ),
            ],
            hotels=[
                Hotel(
                    id="hotel_001",
                    name="Rex Hotel",
                    location=Location(latitude=10.7769, longitude=106.7009),
                ),
            ],
            constraints=TravelConstraints(num_days=1),
        )
        assert len(req.pois) == 1
        assert len(req.hotels) == 1
        assert req.constraints.num_days == 1
        assert req.day_plans is None

    def test_full_request_with_day_plans(self):
        req = TravelPlanRequest(
            pois=[
                POI(
                    id="poi_001",
                    name="Bến Thành",
                    category="market",
                    location=Location(latitude=10.7721, longitude=106.6980),
                    visit_duration_min=60,
                ),
                POI(
                    id="poi_002",
                    name="War Museum",
                    category="museum",
                    location=Location(latitude=10.7798, longitude=106.6922),
                    visit_duration_min=90,
                    entrance_fee=40000.0,
                ),
            ],
            hotels=[
                Hotel(
                    id="hotel_001",
                    name="Rex Hotel",
                    location=Location(latitude=10.7769, longitude=106.7009),
                    assigned_days=[0, 1],
                ),
            ],
            day_plans=[
                DayPlan(day_index=0, date="2025-06-15"),
                DayPlan(day_index=1, date="2025-06-16"),
            ],
            constraints=TravelConstraints(
                num_days=2,
                budget_total=3000000.0,
                transport_modes=[TransportMode.WALKING, TransportMode.TAXI],
            ),
        )
        assert len(req.pois) == 2
        assert len(req.day_plans) == 2
        assert req.constraints.budget_total == 3000000.0

    def test_request_with_budget_constraint(self):
        req = TravelPlanRequest(
            pois=[
                POI(
                    id="poi_003",
                    name="Cu Chi",
                    category="historical",
                    location=Location(latitude=11.14, longitude=106.46),
                    visit_duration_min=180,
                    entrance_fee=110000.0,
                ),
            ],
            hotels=[
                Hotel(
                    id="h1",
                    name="H",
                    location=Location(latitude=10.77, longitude=106.70),
                ),
            ],
            constraints=TravelConstraints(
                num_days=1,
                budget_total=100000.0,
            ),
        )
        total_fee = sum(p.entrance_fee for p in req.pois)
        assert total_fee > req.constraints.budget_total
