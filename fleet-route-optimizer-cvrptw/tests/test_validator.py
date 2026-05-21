"""Tests for ItineraryValidator — Phase 1B."""

import pytest
from src.services.itinerary_validator import ItineraryValidator, ValidationIssue, ValidationResult
from src.models.domain import (
    POI, Location, TimeWindow, TravelItineraryDay, TravelItineraryStop,
)


def _make_poi(id, name, category="culture", intensity="medium", is_outdoor=False, meal_type=None):
    return POI(
        id=id, name=name, category=category,
        location=Location(latitude=16.46, longitude=107.59),
        visit_duration_min=60,
        time_window=TimeWindow(start_min=480, end_min=1260),
        intensity=intensity, is_outdoor=is_outdoor, meal_type=meal_type,
    )


def _make_stop(poi_id, poi_name, arrival, duration=60, travel=10):
    return TravelItineraryStop(
        poi_id=poi_id, poi_name=poi_name,
        location=Location(latitude=16.46, longitude=107.59),
        arrival_time_min=arrival,
        departure_time_min=arrival + duration,
        visit_duration_min=duration,
        travel_time_from_prev_min=travel,
        entrance_fee=0,
    )


def _make_day(day_index, stops):
    return TravelItineraryDay(
        day_index=day_index, date="2025-01-01",
        start_hotel_name="Hotel", start_hotel_location=Location(latitude=16.46, longitude=107.59),
        end_hotel_name="Hotel", end_hotel_location=Location(latitude=16.46, longitude=107.59),
        stops=stops,
        total_travel_min=sum(s.travel_time_from_prev_min for s in stops),
        total_visit_min=sum(s.visit_duration_min for s in stops),
        total_distance_km=5.0,
        total_entrance_fee=0,
        num_pois=len(stops),
    )


class TestMealTiming:
    def test_long_day_no_lunch_warns(self):
        """10-hour day with no lunch POI → meal_missing warning."""
        stops = [
            _make_stop("p1", "Temple A", arrival=480, duration=90),
            _make_stop("p2", "Museum B", arrival=600, duration=120),
            _make_stop("p3", "Park C", arrival=780, duration=90),
            _make_stop("p4", "Palace D", arrival=900, duration=120),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Temple A", "temple"),
            "p2": _make_poi("p2", "Museum B", "museum"),
            "p3": _make_poi("p3", "Park C", "park"),
            "p4": _make_poi("p4", "Palace D", "palace"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        meal_issues = [i for i in result.issues if i.rule == "meal_missing"]
        assert len(meal_issues) >= 1

    def test_day_with_lunch_ok(self):
        """Day with a restaurant in lunch window → no meal warning."""
        stops = [
            _make_stop("p1", "Temple A", arrival=480, duration=90),
            _make_stop("r1", "Bún Bò Huế", arrival=690, duration=60),
            _make_stop("p2", "Museum B", arrival=780, duration=120),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Temple A", "temple"),
            "r1": _make_poi("r1", "Bún Bò Huế", "restaurant", meal_type="lunch"),
            "p2": _make_poi("p2", "Museum B", "museum"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        meal_issues = [i for i in result.issues if i.rule == "meal_missing"]
        assert len(meal_issues) == 0

    def test_short_day_skips_meal_check(self):
        """<5h day → no meal check needed."""
        stops = [
            _make_stop("p1", "Cafe A", arrival=480, duration=60),
            _make_stop("p2", "Cafe B", arrival=570, duration=60),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Cafe A", "cafe"),
            "p2": _make_poi("p2", "Cafe B", "cafe"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        meal_issues = [i for i in result.issues if i.rule == "meal_missing"]
        assert len(meal_issues) == 0


class TestConsecutiveHeavy:
    def test_three_heavy_warns(self):
        """3 consecutive heavy POIs → consecutive_heavy warning."""
        stops = [
            _make_stop("p1", "Temple A", arrival=480, duration=90),
            _make_stop("p2", "Palace B", arrival=600, duration=90),
            _make_stop("p3", "Heritage C", arrival=720, duration=90),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Temple A", "temple", intensity="heavy"),
            "p2": _make_poi("p2", "Palace B", "palace", intensity="heavy"),
            "p3": _make_poi("p3", "Heritage C", "heritage", intensity="heavy"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        heavy_issues = [i for i in result.issues if i.rule == "consecutive_heavy"]
        assert len(heavy_issues) >= 1

    def test_two_heavy_ok(self):
        """2 consecutive heavy (within limit) → no warning."""
        stops = [
            _make_stop("p1", "Temple A", arrival=480, duration=90),
            _make_stop("p2", "Palace B", arrival=600, duration=90),
            _make_stop("c1", "Cafe C", arrival=720, duration=30),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Temple A", "temple", intensity="heavy"),
            "p2": _make_poi("p2", "Palace B", "palace", intensity="heavy"),
            "c1": _make_poi("c1", "Cafe C", "cafe", intensity="light"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        heavy_issues = [i for i in result.issues if i.rule == "consecutive_heavy"]
        assert len(heavy_issues) == 0


class TestOutdoorHeat:
    def test_outdoor_in_heat_window(self):
        """Outdoor POI at 12:30 → outdoor_heat info."""
        stops = [
            _make_stop("p1", "Park A", arrival=750, duration=60),  # 12:30
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Park A", "park", is_outdoor=True),
        }
        result = ItineraryValidator().validate([day], poi_map)
        outdoor_issues = [i for i in result.issues if i.rule == "outdoor_heat"]
        assert len(outdoor_issues) >= 1

    def test_indoor_in_heat_window_ok(self):
        """Indoor POI at 12:30 → no outdoor_heat issue."""
        stops = [
            _make_stop("p1", "Museum A", arrival=750, duration=60),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Museum A", "museum", is_outdoor=False),
        }
        result = ItineraryValidator().validate([day], poi_map)
        outdoor_issues = [i for i in result.issues if i.rule == "outdoor_heat"]
        assert len(outdoor_issues) == 0


class TestQualityScore:
    def test_perfect_score(self):
        """No issues → score 1.0."""
        result = ItineraryValidator().validate([], {})
        assert result.score == 1.0
        assert result.is_valid is True

    def test_score_decreases_with_issues(self):
        """Score decreases with warnings."""
        stops = [
            _make_stop("p1", "Temple A", arrival=480, duration=90),
            _make_stop("p2", "Palace B", arrival=600, duration=90),
            _make_stop("p3", "Heritage C", arrival=720, duration=90),
            _make_stop("p4", "Temple D", arrival=900, duration=120),
        ]
        day = _make_day(0, stops)
        poi_map = {
            "p1": _make_poi("p1", "Temple A", "temple", intensity="heavy"),
            "p2": _make_poi("p2", "Palace B", "palace", intensity="heavy"),
            "p3": _make_poi("p3", "Heritage C", "heritage", intensity="heavy"),
            "p4": _make_poi("p4", "Temple D", "temple", intensity="heavy"),
        }
        result = ItineraryValidator().validate([day], poi_map)
        assert result.score < 1.0
