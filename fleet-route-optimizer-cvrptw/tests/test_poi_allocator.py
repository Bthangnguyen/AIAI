"""Tests for POI Allocator (Stage 1 of Two-Stage solver)."""
import pytest
from src.models.domain import Location, TimeWindow, POI, Hotel, DayPlan, TravelConstraints
from src.services.poi_allocator import POIAllocator


class TestPOIAllocator:
    """Test POI allocation to days."""

    def _make_poi(self, id, lat, lon, duration=60, fee=0.0, priority=0.5, tw_start=480, tw_end=1260):
        return POI(
            id=id, name=f"POI {id}", category="test",
            location=Location(latitude=lat, longitude=lon),
            visit_duration_min=duration, entrance_fee=fee,
            priority_score=priority,
            time_window=TimeWindow(start_min=tw_start, end_min=tw_end),
        )

    def _make_hotel(self, id, lat, lon, days=None):
        return Hotel(
            id=id, name=f"Hotel {id}",
            location=Location(latitude=lat, longitude=lon),
            assigned_days=days,
        )

    def test_single_day_all_pois_fit(self):
        pois = [self._make_poi("p1", 10.77, 106.70, duration=60)]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert len(result.day_assignments) == 1
        assert "p1" in result.day_assignments[0]

    def test_two_days_geo_clustering(self):
        """POIs near hotel1 go to day0, POIs near hotel2 go to day1."""
        pois = [
            self._make_poi("north1", 10.85, 106.70),
            self._make_poi("north2", 10.86, 106.71),
            self._make_poi("south1", 10.70, 106.70),
            self._make_poi("south2", 10.69, 106.71),
        ]
        hotels = [
            self._make_hotel("h_north", 10.87, 106.70, days=[0]),
            self._make_hotel("h_south", 10.68, 106.70, days=[1]),
        ]
        days = [
            DayPlan(day_index=0, date="2025-06-15", hotel_id="h_north"),
            DayPlan(day_index=1, date="2025-06-16", hotel_id="h_south"),
        ]
        constraints = TravelConstraints(num_days=2)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert "north1" in result.day_assignments[0]
        assert "north2" in result.day_assignments[0]
        assert "south1" in result.day_assignments[1]
        assert "south2" in result.day_assignments[1]

    def test_capacity_overflow_drops_lowest_priority(self):
        """When POIs exceed daily capacity, drop lowest priority."""
        pois = [
            self._make_poi("p1", 10.77, 106.70, duration=300, priority=0.9),
            self._make_poi("p2", 10.77, 106.70, duration=300, priority=0.8),
            self._make_poi("p3", 10.77, 106.70, duration=300, priority=0.2),
        ]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1",
                        max_daily_minutes=600)]
        constraints = TravelConstraints(num_days=1)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert len(result.day_assignments[0]) == 2
        assert "p3" in result.dropped_poi_ids

    def test_budget_soft_filter(self):
        """POIs exceeding budget with low priority are dropped."""
        pois = [
            self._make_poi("cheap", 10.77, 106.70, fee=50000, priority=0.9),
            self._make_poi("expensive", 10.77, 106.70, fee=900000, priority=0.2),
        ]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1, budget_total=100000)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert "cheap" in result.day_assignments[0]
        assert "expensive" in result.dropped_poi_ids
