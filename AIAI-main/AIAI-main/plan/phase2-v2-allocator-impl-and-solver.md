# Phase 2 (Part 2): POI Allocator Implementation + Travel Solver (Stage 2)

> Tiếp nối từ `phase2-v1`.

---

## Task 3: POI Allocator — Full Implementation

**Files:**
- Create: `src/services/poi_allocator.py`

- [ ] **Step 1: Create POIAllocator with AllocationResult**

```python
# src/services/poi_allocator.py
"""POI Allocator — Stage 1 of Two-Stage travel solver.

Assigns POIs to days using combined scoring:
  score = w1 * geo_proximity + w2 * time_compatibility + w3 * priority
Then enforces capacity (max_daily_minutes) and budget constraints.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import math

from ..models.domain import POI, Hotel, DayPlan, TravelConstraints, Location
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class AllocationResult:
    """Result of POI-to-day allocation."""
    day_assignments: Dict[int, List[str]]  # day_index -> list of POI ids
    dropped_poi_ids: List[str] = field(default_factory=list)
    dropped_reasons: Dict[str, str] = field(default_factory=dict)


class POIAllocator:
    """Assigns POIs to travel days using geo + time + hotel scoring."""

    def __init__(self, w_geo: float = 0.5, w_time: float = 0.2, w_priority: float = 0.3):
        self.w_geo = w_geo
        self.w_time = w_time
        self.w_priority = w_priority

    def allocate(
        self,
        pois: List[POI],
        hotels: List[Hotel],
        days: List[DayPlan],
        constraints: TravelConstraints,
    ) -> AllocationResult:
        """Allocate POIs to days.

        Algorithm:
        1. Build hotel lookup (day_index -> hotel)
        2. Soft-filter: drop POIs that are clearly over budget with low priority
        3. Score each (POI, day) pair
        4. Greedy assign: best-scoring POI-day pair first
        5. Enforce capacity per day (max_daily_minutes)
        """
        # Build hotel lookup
        hotel_map = {h.id: h for h in hotels}
        day_hotel = {}
        for day in days:
            if day.hotel_id and day.hotel_id in hotel_map:
                day_hotel[day.day_index] = hotel_map[day.hotel_id]
            elif hotels:
                day_hotel[day.day_index] = hotels[0]

        # Soft budget filter
        remaining_pois, dropped_ids, dropped_reasons = self._soft_budget_filter(
            pois, constraints
        )

        # Score and assign
        day_assignments = {d.day_index: [] for d in days}
        day_used_minutes = {d.day_index: 0 for d in days}
        day_used_budget = {d.day_index: 0.0 for d in days}
        day_limits = {d.day_index: d for d in days}

        budget_per_day = None
        if constraints.budget_total is not None:
            budget_per_day = constraints.budget_total / max(constraints.num_days, 1)

        # Calculate scores for all (poi, day) pairs
        scored_pairs = []
        for poi in remaining_pois:
            for day in days:
                hotel = day_hotel.get(day.day_index)
                score = self._score(poi, day, hotel)
                scored_pairs.append((score, poi, day.day_index))

        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        assigned_poi_ids = set()
        for score, poi, day_idx in scored_pairs:
            if poi.id in assigned_poi_ids:
                continue

            day = day_limits[day_idx]

            # Check capacity
            if day_used_minutes[day_idx] + poi.visit_duration_min > day.max_daily_minutes:
                continue

            # Check max POIs per day
            if len(day_assignments[day_idx]) >= day.max_pois:
                continue

            # Check budget
            if budget_per_day is not None:
                if day_used_budget[day_idx] + poi.entrance_fee > budget_per_day:
                    continue

            # Assign
            day_assignments[day_idx].append(poi.id)
            day_used_minutes[day_idx] += poi.visit_duration_min
            day_used_budget[day_idx] += poi.entrance_fee
            assigned_poi_ids.add(poi.id)

        # Collect unassigned POIs
        for poi in remaining_pois:
            if poi.id not in assigned_poi_ids:
                dropped_ids.append(poi.id)
                dropped_reasons[poi.id] = "capacity_or_budget_overflow"

        logger.info(
            f"POI Allocation: {len(assigned_poi_ids)} assigned, "
            f"{len(dropped_ids)} dropped across {len(days)} days"
        )

        return AllocationResult(
            day_assignments=day_assignments,
            dropped_poi_ids=dropped_ids,
            dropped_reasons=dropped_reasons,
        )

    def _soft_budget_filter(
        self, pois: List[POI], constraints: TravelConstraints
    ) -> tuple:
        """Remove POIs that clearly exceed budget with low value ratio."""
        if constraints.budget_total is None:
            return pois, [], {}

        budget = constraints.budget_total
        dropped_ids = []
        dropped_reasons = {}
        remaining = []

        for poi in pois:
            # Drop if single POI costs >50% of total budget AND priority < 0.3
            if poi.entrance_fee > budget * 0.5 and poi.priority_score < 0.3:
                dropped_ids.append(poi.id)
                dropped_reasons[poi.id] = "budget_soft_filter"
                logger.info(f"Soft-filter dropped: {poi.id} (fee={poi.entrance_fee}, priority={poi.priority_score})")
            else:
                remaining.append(poi)

        return remaining, dropped_ids, dropped_reasons

    def _score(self, poi: POI, day: DayPlan, hotel: Optional[Hotel]) -> float:
        """Score a (POI, day) pair. Higher = better fit."""
        geo_score = 0.0
        if hotel:
            dist = self._haversine(
                poi.location.latitude, poi.location.longitude,
                hotel.location.latitude, hotel.location.longitude,
            )
            # Normalize: closer = higher score (max 1.0 at 0km, 0.0 at 50+km)
            geo_score = max(0.0, 1.0 - dist / 50.0)

        time_score = 0.0
        if poi.time_window:
            day_mid = (day.start_time_min + day.end_time_min) / 2
            poi_mid = (poi.time_window.start_min + poi.time_window.end_min) / 2
            # Closer midpoints = better time compatibility
            time_diff = abs(day_mid - poi_mid)
            time_score = max(0.0, 1.0 - time_diff / 720.0)  # 12h max diff
        else:
            time_score = 0.5  # neutral if no time window

        priority_score = poi.priority_score

        return (
            self.w_geo * geo_score
            + self.w_time * time_score
            + self.w_priority * priority_score
        )

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(a))
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_poi_allocator.py -v`
Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: implement POIAllocator (Stage 1 geo+time+priority scoring)"
```

---

## Task 4: Travel Solver Adapter (Stage 2)

**Files:**
- Create: `src/services/travel_solver.py`
- Create: `tests/test_travel_solver.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_travel_solver.py
"""Tests for Travel Solver Adapter (Stage 2)."""
import pytest
from src.models.domain import Location, TimeWindow, POI, Hotel, DayPlan
from src.services.travel_solver import TravelSolverAdapter


class TestTravelSolverAdapter:
    """Test the adapter that converts travel data to CVRPTW format."""

    def _make_poi(self, id, lat, lon, duration=60, fee=0.0, tw_start=480, tw_end=1260):
        return POI(
            id=id, name=f"POI {id}", category="test",
            location=Location(latitude=lat, longitude=lon),
            visit_duration_min=duration, entrance_fee=fee,
            priority_score=0.5,
            time_window=TimeWindow(start_min=tw_start, end_min=tw_end),
        )

    def test_build_problem_data(self):
        """Adapter correctly maps travel models to solver ProblemData format."""
        pois = [
            self._make_poi("p1", 10.77, 106.70, duration=60),
            self._make_poi("p2", 10.78, 106.71, duration=90),
        ]
        hotel = Hotel(
            id="h1", name="Hotel",
            location=Location(latitude=10.76, longitude=106.69),
        )
        day = DayPlan(
            day_index=0, date="2025-06-15", hotel_id="h1",
            max_daily_minutes=600, start_time_min=480, end_time_min=1260,
        )

        adapter = TravelSolverAdapter()
        problem = adapter.build_problem_data(pois, hotel, day)

        # Locations: hotel (depot=0), then POIs
        assert len(problem["locations"]) == 3
        assert problem["locations"][0] == (10.76, 106.69)  # hotel
        assert problem["depot"] == 0
        assert problem["num_vehicles"] == 1

        # Demands = visit_duration_min (capacity model)
        assert problem["demands"] == [0, 60, 90]

        # Vehicle capacity = max_daily_minutes
        assert problem["vehicle_capacities"] == [600]

        # Time windows
        assert problem["time_windows"][0] == (480, 1260)  # depot
        assert problem["time_windows"][1] == (480, 1260)  # p1
        assert problem["time_windows"][2] == (480, 1260)  # p2

    def test_build_problem_coord_type(self):
        pois = [self._make_poi("p1", 10.77, 106.70)]
        hotel = Hotel(id="h1", name="H", location=Location(latitude=10.76, longitude=106.69))
        day = DayPlan(day_index=0, date="2025-06-15", hotel_id="h1")

        adapter = TravelSolverAdapter()
        problem = adapter.build_problem_data(pois, hotel, day)

        assert problem["coord_type"] == "latlon"
        assert problem["service_time"] == 0  # service time embedded in demands
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_travel_solver.py -v`
Expected: FAIL `ImportError`

- [ ] **Step 3: Implement TravelSolverAdapter**

```python
# src/services/travel_solver.py
"""Travel Solver Adapter — Stage 2 of Two-Stage solver.

Converts travel domain models (POI, Hotel, DayPlan) into the
ProblemData format that ORToolsSolverImpl expects, then runs the solver
and converts the solution back to TravelItineraryDay.
"""

from typing import List, Dict, Optional
from ..models.domain import (
    POI, Hotel, DayPlan, Location,
    TravelItineraryStop, TravelItineraryDay,
)
from ..core.solvers import create_solver
from ..config import get_logger

logger = get_logger(__name__)


class TravelSolverAdapter:
    """Adapts travel models to CVRPTW solver input and interprets output."""

    def build_problem_data(
        self, pois: List[POI], hotel: Hotel, day: DayPlan
    ) -> Dict:
        """Convert travel models to solver-compatible ProblemData dict.

        Mapping:
        - Hotel → depot (index 0)
        - POIs → locations (index 1..N)
        - visit_duration_min → demand (capacity = max_daily_minutes)
        - POI.time_window → time_windows
        - service_time = 0 (visit_duration is already in demand/capacity model)
        """
        # Locations: depot first, then POIs
        locations = [hotel.location.as_tuple()]
        locations += [poi.location.as_tuple() for poi in pois]

        # Demands: depot=0, POI=visit_duration_min
        demands = [0] + [poi.visit_duration_min for poi in pois]

        # Time windows
        depot_tw = (day.start_time_min, day.end_time_min)
        time_windows = [depot_tw]
        for poi in pois:
            if poi.time_window:
                time_windows.append((poi.time_window.start_min, poi.time_window.end_min))
            else:
                time_windows.append(depot_tw)  # fallback to full day

        return {
            "locations": locations,
            "demands": demands,
            "time_windows": time_windows,
            "vehicle_capacities": [day.max_daily_minutes],
            "num_vehicles": 1,
            "depot": 0,
            "service_time": 0,
            "coord_type": "latlon",
        }

    def solve_day(
        self,
        pois: List[POI],
        hotel: Hotel,
        day: DayPlan,
        time_limit: int = 30,
        solver_type: str = "ortools",
    ) -> Optional[TravelItineraryDay]:
        """Solve routing for a single day.

        Args:
            pois: POIs assigned to this day
            hotel: Hotel (depot) for this day
            day: DayPlan with constraints
            time_limit: Solver time limit in seconds
            solver_type: Solver to use

        Returns:
            TravelItineraryDay or None if no solution
        """
        if not pois:
            return TravelItineraryDay(
                day_index=day.day_index, date=day.date,
                hotel_name=hotel.name, hotel_location=hotel.location,
                stops=[], total_travel_min=0, total_visit_min=0,
                total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
            )

        problem = self.build_problem_data(pois, hotel, day)
        poi_lookup = {i + 1: pois[i] for i in range(len(pois))}

        solver = create_solver(solver_type, problem)
        solution = solver.solve(
            time_limit_seconds=time_limit,
            vehicle_penalty_weight=0,
            distance_weight=1.0,
        )

        if not solution or solution.get("status") == "error":
            logger.warning(f"Day {day.day_index}: No solution found")
            return None

        # Extract the single route (we have 1 vehicle)
        routes = solution.get("routes", [])
        if not routes:
            return None

        route = routes[0]
        stops = []
        total_fee = 0.0

        for stop_data in route.get("route", []):
            loc_idx = stop_data["location"]
            if loc_idx == 0:
                continue  # skip depot

            poi = poi_lookup.get(loc_idx)
            if not poi:
                continue

            stop = TravelItineraryStop(
                poi_id=poi.id,
                poi_name=poi.name,
                location=poi.location,
                arrival_time_min=int(stop_data.get("time", 0)),
                departure_time_min=int(stop_data.get("time", 0)) + poi.visit_duration_min,
                visit_duration_min=poi.visit_duration_min,
                travel_time_from_prev_min=0,
                entrance_fee=poi.entrance_fee,
            )
            stops.append(stop)
            total_fee += poi.entrance_fee

        return TravelItineraryDay(
            day_index=day.day_index,
            date=day.date,
            hotel_name=hotel.name,
            hotel_location=hotel.location,
            stops=stops,
            total_travel_min=int(route.get("travel_time_minutes", 0)),
            total_visit_min=sum(s.visit_duration_min for s in stops),
            total_distance_km=round(route.get("distance_km", 0.0), 2),
            total_entrance_fee=total_fee,
            num_pois=len(stops),
        )
```

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_travel_solver.py -v`
Expected: 2 PASSED

```bash
git add -A && git commit -m "feat: implement TravelSolverAdapter (Stage 2)"
```
