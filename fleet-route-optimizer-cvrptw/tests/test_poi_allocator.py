"""Tests for POI Allocator (Category-First algorithm)."""
import pytest
from src.models.domain import Location, TimeWindow, POI, Hotel, DayPlan, TravelConstraints
from src.services.poi_allocator import POIAllocator


class TestPOIAllocator:
    """Test POI allocation to days with category balancing."""

    def _make_poi(self, id, lat, lon, category="culture", category_group=None,
                  duration=60, fee=0.0, priority=0.5, tw_start=480, tw_end=1260):
        return POI(
            id=id, name=f"POI {id}", category=category,
            category_group=category_group or category,
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
        pois = [self._make_poi("p1", 10.77, 106.70, category="culture", duration=60)]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert len(result.day_assignments) == 1
        assert "p1" in result.day_assignments[0]

    def test_category_balance_across_days(self):
        """3 food + 3 culture + 2 cafe across 3 days should be balanced."""
        pois = [
            self._make_poi("f1", 16.46, 107.59, category="food", category_group="food", priority=0.8),
            self._make_poi("f2", 16.46, 107.60, category="food", category_group="food", priority=0.7),
            self._make_poi("f3", 16.47, 107.59, category="food", category_group="food", priority=0.6),
            self._make_poi("c1", 16.47, 107.60, category="culture", category_group="culture", priority=0.9),
            self._make_poi("c2", 16.46, 107.58, category="culture", category_group="culture", priority=0.8),
            self._make_poi("c3", 16.45, 107.59, category="culture", category_group="culture", priority=0.7),
            self._make_poi("ca1", 16.47, 107.61, category="cafe", category_group="cafe", priority=0.6),
            self._make_poi("ca2", 16.46, 107.61, category="cafe", category_group="cafe", priority=0.5),
        ]
        hotels = [
            self._make_hotel("h1", 16.46, 107.59, days=[0]),
            self._make_hotel("h2", 16.46, 107.59, days=[1]),
            self._make_hotel("h3", 16.46, 107.59, days=[2]),
        ]
        days = [
            DayPlan(day_index=0, date="Day 1", hotel_id="h1"),
            DayPlan(day_index=1, date="Day 2", hotel_id="h2"),
            DayPlan(day_index=2, date="Day 3", hotel_id="h3"),
        ]
        constraints = TravelConstraints(
            num_days=3,
            target_category_distribution={
                "culture": 0.375,  # 3/8
                "food": 0.375,    # 3/8
                "cafe": 0.25,     # 2/8
            }
        )

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        # All 8 should be assigned
        total_assigned = sum(len(v) for v in result.day_assignments.values())
        assert total_assigned == 8

        # Each day should have at least 1 culture and 1 food
        for day_idx in range(3):
            day_pois = result.day_assignments[day_idx]
            day_categories = set()
            for pid in day_pois:
                for p in pois:
                    if p.id == pid:
                        day_categories.add(p.category_group)
            assert "culture" in day_categories, f"Day {day_idx} missing culture"
            assert "food" in day_categories, f"Day {day_idx} missing food"

    def test_food_tour_heavy_food_distribution(self):
        """Food tour: distribution food=0.80 should give mostly food POIs."""
        pois = [
            self._make_poi("f1", 16.46, 107.59, category="food", category_group="food"),
            self._make_poi("f2", 16.46, 107.60, category="food", category_group="food"),
            self._make_poi("f3", 16.47, 107.59, category="food", category_group="food"),
            self._make_poi("f4", 16.47, 107.60, category="food", category_group="food"),
            self._make_poi("c1", 16.46, 107.58, category="culture", category_group="culture"),
        ]
        hotels = [self._make_hotel("h1", 16.46, 107.59, days=[0])]
        days = [DayPlan(day_index=0, date="Day 1", hotel_id="h1")]
        constraints = TravelConstraints(
            num_days=1,
            target_category_distribution={"food": 0.80, "culture": 0.20}
        )

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        # 5 POIs * 0.80 = 4 food quota, 5 * 0.20 = 1 culture
        food_count = sum(1 for pid in result.day_assignments[0]
                        if any(p.id == pid and p.category_group == "food" for p in pois))
        assert food_count >= 3  # At least 3 food (4 ideally)

    def test_capacity_overflow_drops(self):
        """When POIs exceed daily capacity, overflow goes to dropped."""
        pois = [
            self._make_poi("p1", 10.77, 106.70, category="culture", duration=300, priority=0.9),
            self._make_poi("p2", 10.77, 106.70, category="food", duration=300, priority=0.8),
            self._make_poi("p3", 10.77, 106.70, category="cafe", duration=300, priority=0.2),
        ]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1",
                        max_daily_minutes=600)]
        constraints = TravelConstraints(num_days=1)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert len(result.day_assignments[0]) == 2
        assert len(result.dropped_poi_ids) >= 1

    def test_budget_soft_filter(self):
        """POIs exceeding budget with low priority are dropped."""
        pois = [
            self._make_poi("cheap", 10.77, 106.70, category="food", fee=50000, priority=0.9),
            self._make_poi("expensive", 10.77, 106.70, category="culture", fee=900000, priority=0.2),
        ]
        hotels = [self._make_hotel("h1", 10.78, 106.70, days=[0])]
        days = [DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1, budget_total=100000)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        assert "cheap" in result.day_assignments[0]
        assert "expensive" in result.dropped_poi_ids

    def test_fallback_when_no_distribution(self):
        """When no distribution provided, uses DEFAULT_DISTRIBUTION."""
        pois = [
            self._make_poi("f1", 16.46, 107.59, category="food", category_group="food"),
            self._make_poi("c1", 16.46, 107.60, category="culture", category_group="culture"),
            self._make_poi("ca1", 16.47, 107.59, category="cafe", category_group="cafe"),
        ]
        hotels = [self._make_hotel("h1", 16.46, 107.59, days=[0])]
        days = [DayPlan(day_index=0, date="Day 1", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1)  # No distribution

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        # All 3 should be assigned (different categories)
        assert len(result.day_assignments[0]) == 3

    def test_category_group_auto_resolve(self):
        """When category_group is not set, it should auto-resolve from category."""
        pois = [
            self._make_poi("r1", 16.46, 107.59, category="restaurant", category_group=None),
            self._make_poi("t1", 16.46, 107.60, category="temple", category_group=None),
        ]
        hotels = [self._make_hotel("h1", 16.46, 107.59, days=[0])]
        days = [DayPlan(day_index=0, date="Day 1", hotel_id="h1")]
        constraints = TravelConstraints(num_days=1)

        allocator = POIAllocator()
        result = allocator.allocate(pois, hotels, days, constraints)

        # Both should be assigned
        assert len(result.day_assignments[0]) == 2

    def test_quota_computation(self):
        """Verify largest-remainder quota computation."""
        allocator = POIAllocator()
        distribution = {
            "food": 0.25, "culture": 0.30, "cafe": 0.15,
            "nature": 0.15, "nightlife": 0.05, "shopping": 0.05,
            "art": 0.03, "wellness": 0.02,
        }
        # Build mock available pools
        available = {
            "food": [None] * 10,
            "culture": [None] * 10,
            "cafe": [None] * 10,
            "nature": [None] * 10,
            "nightlife": [None] * 10,
            "shopping": [None] * 10,
            "art": [None] * 10,
            "wellness": [None] * 10,
        }
        quotas = allocator._compute_quotas(distribution, 9, available)

        assert sum(quotas.values()) == 9
        assert quotas.get("culture", 0) >= 2  # 0.30 * 9 = 2.7 → 3
        assert quotas.get("food", 0) >= 2     # 0.25 * 9 = 2.25 → 2
