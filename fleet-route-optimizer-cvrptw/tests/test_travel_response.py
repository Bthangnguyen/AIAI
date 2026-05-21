"""Tests for travel itinerary response models."""
import pytest
from src.models.domain import (
    Location, TravelItineraryStop, TravelItineraryDay, TravelItinerary,
)


class TestTravelItineraryStop:
    def test_stop_creation(self):
        stop = TravelItineraryStop(
            poi_id="poi_001",
            poi_name="Bến Thành Market",
            location=Location(latitude=10.7721, longitude=106.6980),
            arrival_time_min=510,
            departure_time_min=570,
            visit_duration_min=60,
            travel_time_from_prev_min=30,
            entrance_fee=0.0,
        )
        assert stop.poi_id == "poi_001"
        assert stop.arrival_time_min == 510
        assert stop.departure_time_min == 570


class TestTravelItineraryDay:
    def test_day_creation(self):
        day = TravelItineraryDay(
            day_index=0,
            date="2025-06-15",
            start_hotel_name="Rex Hotel",
            start_hotel_location=Location(latitude=10.7769, longitude=106.7009),
            stops=[],
            total_travel_min=0,
            total_visit_min=0,
            total_distance_km=0.0,
            total_entrance_fee=0.0,
            num_pois=0,
        )
        assert day.day_index == 0
        assert day.num_pois == 0


class TestTravelItinerary:
    def test_itinerary_creation(self):
        itinerary = TravelItinerary(
            status="success",
            num_days=3,
            days=[],
            total_pois_visited=0,
            total_pois_dropped=2,
            total_entrance_fee=0.0,
            total_travel_min=0,
            total_distance_km=0.0,
            budget_total=5000000.0,
            budget_used=0.0,
            dropped_pois=[],
        )
        assert itinerary.status == "success"
        assert itinerary.num_days == 3
        assert itinerary.total_pois_dropped == 2
