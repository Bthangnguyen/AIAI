# Phase 2 (Part 1): Design Overview + POI Allocator (Stage 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Adapt OR-Tools CVRPTW solver from logistics to travel using Two-Stage approach.

**Architecture:** Stage 1 assigns POIs to days via scoring (geo + time + hotel). Stage 2 solves each day's route independently using existing OR-Tools solver with adapted constraints.

**Tech Stack:** Python 3.10+, OR-Tools 9.7+, Pydantic 2.0+, pytest

---

## Design Decisions (Confirmed)

| Decision | Choice |
|---|---|
| Multi-day strategy | **Two-Stage** (cluster → solve per day) |
| Stage 1 algorithm | **Combined scoring** (geo + time + hotel proximity) |
| Budget enforcement | **Hybrid** (soft-filter + solver AddDimension) |
| Capacity mapping | `max_daily_minutes` = capacity, `visit_duration_min` = demand |
| Service time | Direct from `POI.visit_duration_min` (no formula) |

## File Structure — Phase 2

```
src/services/
├── poi_allocator.py         # CREATE: Stage 1 — assign POIs to days
├── travel_solver.py         # CREATE: Stage 2 — adapt OR-Tools for travel
├── travel_plan_service.py   # CREATE: Orchestrate Stage1 + Stage2
├── problem_builder.py       # KEEP (legacy, untouched)
├── solver_service.py        # KEEP (legacy, untouched)
├── distance_cache.py        # KEEP (used by travel_solver)
src/api/
├── routes.py                # MODIFY: add POST /plan endpoint
src/models/
├── domain.py                # MODIFY: add TravelItineraryDay, TravelItinerary
tests/
├── test_poi_allocator.py    # CREATE
├── test_travel_solver.py    # CREATE
├── test_travel_plan_service.py  # CREATE
```

---

## Task 1: Add response models (TravelItineraryDay, TravelItinerary)

**Files:**
- Modify: `src/models/domain.py`
- Create: `tests/test_travel_response.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_travel_response.py
"""Tests for travel itinerary response models."""
import pytest
from src.models.domain import (
    Location, TimeWindow, TravelItineraryStop,
    TravelItineraryDay, TravelItinerary,
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
            hotel_name="Rex Hotel",
            hotel_location=Location(latitude=10.7769, longitude=106.7009),
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_response.py -v`
Expected: FAIL `ImportError`

- [ ] **Step 3: Add models to domain.py**

Append after `TravelConstraints` in `src/models/domain.py`:

```python
class TravelItineraryStop(BaseModel):
    """A single stop in a day's itinerary."""
    poi_id: str = Field(..., description="POI identifier")
    poi_name: str = Field(..., description="POI display name")
    location: Location = Field(..., description="Stop coordinates")
    arrival_time_min: int = Field(..., description="Arrival time (minutes from midnight)")
    departure_time_min: int = Field(..., description="Departure time (minutes from midnight)")
    visit_duration_min: int = Field(..., description="Time spent at this POI")
    travel_time_from_prev_min: int = Field(0, description="Travel time from previous stop")
    entrance_fee: float = Field(0.0, description="Entrance fee paid at this POI")


class TravelItineraryDay(BaseModel):
    """One day's optimized itinerary."""
    day_index: int = Field(..., description="0-based day index")
    date: str = Field(..., description="Date YYYY-MM-DD")
    hotel_name: str = Field(..., description="Hotel name for this day")
    hotel_location: Location = Field(..., description="Hotel coordinates (start/end)")
    stops: List[TravelItineraryStop] = Field(..., description="Ordered POI stops")
    total_travel_min: int = Field(..., description="Total travel time in minutes")
    total_visit_min: int = Field(..., description="Total visit time in minutes")
    total_distance_km: float = Field(..., description="Total distance traveled")
    total_entrance_fee: float = Field(0.0, description="Total entrance fees for this day")
    num_pois: int = Field(..., description="Number of POIs visited")


class TravelItinerary(BaseModel):
    """Complete multi-day travel itinerary — final response."""
    status: str = Field("success", description="success or error")
    num_days: int = Field(..., description="Number of days")
    days: List[TravelItineraryDay] = Field(..., description="Per-day itineraries")
    total_pois_visited: int = Field(..., description="Total POIs across all days")
    total_pois_dropped: int = Field(0, description="POIs not included")
    total_entrance_fee: float = Field(0.0, description="Total entrance fees")
    total_travel_min: int = Field(0, description="Total travel time")
    total_distance_km: float = Field(0.0, description="Total distance")
    budget_total: Optional[float] = Field(None, description="Budget limit")
    budget_used: float = Field(0.0, description="Budget consumed")
    dropped_pois: Optional[List[Dict]] = Field(None, description="POIs not visited")
    solver: Optional[str] = Field(None, description="Solver used")
    message: Optional[str] = Field(None, description="Error/info message")
```

- [ ] **Step 4: Update `__init__.py` exports**

Add to `src/models/__init__.py` imports and `__all__`:
`TravelItineraryStop`, `TravelItineraryDay`, `TravelItinerary`

- [ ] **Step 5: Run tests, commit**

Run: `python -m pytest tests/test_travel_response.py -v`
Expected: 3 PASSED

```bash
git add -A && git commit -m "feat: add TravelItinerary response models"
```

---

## Task 2: POI Allocator — Stage 1 (assign POIs to days)

**Files:**
- Create: `src/services/poi_allocator.py`
- Create: `tests/test_poi_allocator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_poi_allocator.py
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

        # North POIs should be assigned to day 0 (near h_north)
        assert "north1" in result.day_assignments[0]
        assert "north2" in result.day_assignments[0]
        # South POIs should be assigned to day 1 (near h_south)
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
        assert "p3" in result.dropped_poi_ids  # lowest priority dropped

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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_poi_allocator.py -v`
Expected: FAIL `ImportError: cannot import name 'POIAllocator'`

- [ ] **Step 3: Implement POIAllocator** — see phase2-v2 for full implementation

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_poi_allocator.py -v`
Expected: 4 PASSED

```bash
git add -A && git commit -m "feat: add POIAllocator (Stage 1 clustering)"
```
