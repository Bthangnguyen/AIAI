"""Tests for travel domain models."""
import pytest
from src.models.domain import (
    Location, TimeWindow, POI, Hotel, DayPlan,
    TravelConstraints, TransportMode,
)


class TestPOIModel:
    """Test POI (Point of Interest) model."""

    def test_poi_basic_creation(self):
        poi = POI(
            id="poi_001",
            name="Bến Thành Market",
            category="market",
            location=Location(latitude=10.7721, longitude=106.6980),
            visit_duration_min=60,
            time_window=TimeWindow(start_min=480, end_min=1260),
            entrance_fee=0.0,
            priority_score=0.85,
        )
        assert poi.id == "poi_001"
        assert poi.name == "Bến Thành Market"
        assert poi.visit_duration_min == 60
        assert poi.entrance_fee == 0.0
        assert poi.priority_score == 0.85

    def test_poi_defaults(self):
        poi = POI(
            id="poi_002",
            name="War Remnants Museum",
            category="museum",
            location=Location(latitude=10.7798, longitude=106.6922),
            visit_duration_min=90,
        )
        assert poi.entrance_fee == 0.0
        assert poi.priority_score == 0.5
        assert poi.time_window is None

    def test_poi_with_entrance_fee(self):
        poi = POI(
            id="poi_003",
            name="Cu Chi Tunnels",
            category="historical",
            location=Location(latitude=11.1415, longitude=106.4635),
            visit_duration_min=180,
            entrance_fee=110000.0,
        )
        assert poi.entrance_fee == 110000.0


class TestHotelModel:
    """Test Hotel model (replaces Depot for travel)."""

    def test_hotel_basic(self):
        hotel = Hotel(
            id="hotel_001",
            name="Rex Hotel Saigon",
            location=Location(latitude=10.7769, longitude=106.7009),
            check_in_time=840,
            check_out_time=720,
        )
        assert hotel.id == "hotel_001"
        assert hotel.check_in_time == 840
        assert hotel.check_out_time == 720

    def test_hotel_defaults(self):
        hotel = Hotel(
            id="hotel_002",
            name="Budget Hostel",
            location=Location(latitude=10.770, longitude=106.695),
        )
        assert hotel.check_in_time == 840
        assert hotel.check_out_time == 720

    def test_hotel_with_day_assignment(self):
        hotel = Hotel(
            id="hotel_003",
            name="Mekong Lodge",
            location=Location(latitude=10.35, longitude=106.36),
            assigned_days=[0, 1],
        )
        assert hotel.assigned_days == [0, 1]


class TestDayPlanModel:
    """Test DayPlan model (replaces Vehicle for travel)."""

    def test_dayplan_basic(self):
        plan = DayPlan(
            day_index=0,
            date="2025-06-15",
            start_time_min=480,
            end_time_min=1260,
            max_daily_minutes=480,
            max_pois=8,
        )
        assert plan.day_index == 0
        assert plan.date == "2025-06-15"
        assert plan.max_daily_minutes == 480
        assert plan.max_pois == 8

    def test_dayplan_defaults(self):
        plan = DayPlan(
            day_index=1,
            date="2025-06-16",
        )
        assert plan.start_time_min == 480
        assert plan.end_time_min == 1260
        assert plan.max_daily_minutes == 600
        assert plan.max_pois == 10

    def test_dayplan_with_hotel_ref(self):
        plan = DayPlan(
            day_index=0,
            date="2025-06-15",
            hotel_id="hotel_001",
        )
        assert plan.hotel_id == "hotel_001"


class TestTravelConstraintsModel:
    """Test TravelConstraints — hard constraints from user."""

    def test_constraints_basic(self):
        tc = TravelConstraints(
            budget_total=5000000.0,
            transport_modes=[TransportMode.WALKING, TransportMode.TAXI],
            num_days=3,
        )
        assert tc.budget_total == 5000000.0
        assert TransportMode.WALKING in tc.transport_modes
        assert tc.num_days == 3

    def test_constraints_defaults(self):
        tc = TravelConstraints(num_days=2)
        assert tc.budget_total is None
        assert tc.transport_modes == [TransportMode.WALKING, TransportMode.TAXI, TransportMode.BUS]
        assert tc.meal_break_enabled is False
        assert tc.meal_break_duration_min == 60

    def test_transport_mode_enum(self):
        assert TransportMode.WALKING == "walking"
        assert TransportMode.TAXI == "taxi"
        assert TransportMode.BUS == "bus"

    def test_constraints_with_meal_break(self):
        tc = TravelConstraints(
            num_days=1,
            meal_break_enabled=True,
            meal_break_duration_min=45,
            meal_break_window=TimeWindow(start_min=690, end_min=810),
        )
        assert tc.meal_break_enabled is True
        assert tc.meal_break_duration_min == 45
        assert tc.meal_break_window.start_min == 690

