# Phase 2 (Part 3): TravelPlanService Orchestrator + API Endpoint

> Tiếp nối từ `phase2-v2`. Kết nối Stage 1 + Stage 2 + API.

---

## Task 5: TravelPlanService — Orchestrator

**Files:**
- Create: `src/services/travel_plan_service.py`
- Create: `tests/test_travel_plan_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_travel_plan_service.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_travel_plan_service.py -v`
Expected: FAIL `ImportError`

- [ ] **Step 3: Implement TravelPlanService**

```python
# src/services/travel_plan_service.py
"""TravelPlanService — orchestrates the Two-Stage travel solver.

Flow:
  1. Auto-generate DayPlans if not provided
  2. Resolve hotels for each day
  3. Stage 1: POIAllocator assigns POIs to days
  4. Stage 2: TravelSolverAdapter solves each day's route
  5. Assemble TravelItinerary response
"""

from typing import List, Optional
from ..models.domain import (
    POI, Hotel, DayPlan, TravelConstraints,
    TravelItinerary, TravelItineraryDay,
)
from ..models.api import TravelPlanRequest
from .poi_allocator import POIAllocator
from .travel_solver import TravelSolverAdapter
from ..config import get_logger

logger = get_logger(__name__)


class TravelPlanService:
    """Orchestrates travel itinerary planning."""

    def __init__(self):
        self.allocator = POIAllocator()
        self.solver = TravelSolverAdapter()

    def plan(
        self,
        request: TravelPlanRequest,
        time_limit_per_day: int = 30,
        solver_type: str = "ortools",
    ) -> TravelItinerary:
        """Create optimized travel itinerary.

        Args:
            request: TravelPlanRequest from Layer 3
            time_limit_per_day: Solver time limit per day (seconds)
            solver_type: Solver to use

        Returns:
            TravelItinerary with per-day routes
        """
        # 1. Generate day plans if not provided
        day_plans = request.day_plans or self._generate_day_plans(request)

        # 2. Build hotel map
        hotel_map = {h.id: h for h in request.hotels}

        # 3. Stage 1: Allocate POIs to days
        logger.info("Stage 1: Allocating POIs to days...")
        allocation = self.allocator.allocate(
            request.pois, request.hotels, day_plans, request.constraints
        )

        # Build POI lookup
        poi_map = {p.id: p for p in request.pois}

        # 4. Stage 2: Solve each day
        logger.info("Stage 2: Solving routes per day...")
        days_result: List[TravelItineraryDay] = []

        for day in day_plans:
            hotel = self._resolve_hotel(request.hotels, day.day_index)
            poi_ids = allocation.day_assignments.get(day.day_index, [])
            day_pois = [poi_map[pid] for pid in poi_ids if pid in poi_map]

            logger.info(
                f"Day {day.day_index} ({day.date}): "
                f"{len(day_pois)} POIs, hotel={hotel.name}"
            )

            day_result = self.solver.solve_day(
                pois=day_pois,
                hotel=hotel,
                day=day,
                time_limit=time_limit_per_day,
                solver_type=solver_type,
            )

            if day_result:
                days_result.append(day_result)
            else:
                # Empty day fallback
                days_result.append(TravelItineraryDay(
                    day_index=day.day_index, date=day.date,
                    hotel_name=hotel.name, hotel_location=hotel.location,
                    stops=[], total_travel_min=0, total_visit_min=0,
                    total_distance_km=0.0, total_entrance_fee=0.0, num_pois=0,
                ))

        # 5. Assemble response
        total_pois = sum(d.num_pois for d in days_result)
        total_fee = sum(d.total_entrance_fee for d in days_result)
        total_travel = sum(d.total_travel_min for d in days_result)
        total_dist = sum(d.total_distance_km for d in days_result)

        dropped_pois = [
            {"poi_id": pid, "reason": allocation.dropped_reasons.get(pid, "unknown")}
            for pid in allocation.dropped_poi_ids
        ]

        return TravelItinerary(
            status="success",
            num_days=len(days_result),
            days=days_result,
            total_pois_visited=total_pois,
            total_pois_dropped=len(allocation.dropped_poi_ids),
            total_entrance_fee=total_fee,
            total_travel_min=total_travel,
            total_distance_km=round(total_dist, 2),
            budget_total=request.constraints.budget_total,
            budget_used=total_fee,
            dropped_pois=dropped_pois if dropped_pois else None,
            solver=solver_type,
        )

    def _generate_day_plans(self, request: TravelPlanRequest) -> List[DayPlan]:
        """Auto-generate DayPlans from constraints."""
        plans = []
        for i in range(request.constraints.num_days):
            hotel = self._resolve_hotel(request.hotels, i)
            plans.append(DayPlan(
                day_index=i,
                date=f"day-{i}",
                hotel_id=hotel.id if hotel else None,
            ))
        return plans

    def _resolve_hotel(self, hotels: List[Hotel], day_index: int) -> Hotel:
        """Find the hotel assigned to a specific day."""
        for hotel in hotels:
            if hotel.assigned_days and day_index in hotel.assigned_days:
                return hotel
        # Fallback: first hotel
        return hotels[0] if hotels else None
```

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_travel_plan_service.py -v`
Expected: 2 PASSED

```bash
git add -A && git commit -m "feat: implement TravelPlanService orchestrator"
```

---

## Task 6: Add POST /plan API endpoint

**Files:**
- Modify: `src/api/routes.py`

- [ ] **Step 1: Add /plan endpoint after existing routes**

Add to `src/api/routes.py`:

```python
from ..models.api import TravelPlanRequest
from ..services.travel_plan_service import TravelPlanService

# Singleton travel service
travel_service = TravelPlanService()

@router.post('/plan')
async def plan_travel_endpoint(
    request: TravelPlanRequest = Body(...),
    time_limit: int = Query(30, description="Solver time limit per day", ge=1, le=600),
    solver: str = Query("ortools", description="Solver type"),
    _: None = Depends(verify_api_key)
):
    """Create optimized multi-day travel itinerary.

    Accepts POIs, hotels, and constraints from Layer 3.
    Returns optimized per-day routes with timing and costs.
    """
    try:
        result = travel_service.plan(
            request=request,
            time_limit_per_day=time_limit,
            solver_type=solver,
        )
        return result
    except Exception as e:
        logger.exception("Error during travel planning")
        raise HTTPException(status_code=500, detail=f"Planning error: {str(e)}")
```

- [ ] **Step 2: Update services/__init__.py**

Add exports for new services:

```python
from .travel_plan_service import TravelPlanService
from .poi_allocator import POIAllocator
from .travel_solver import TravelSolverAdapter
```

- [ ] **Step 3: Verify server starts**

Run: `cd fleet-route-optimizer-cvrptw && python -c "from src.app import app; print('Server importable OK')"`
Expected: `Server importable OK`

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: add POST /plan endpoint for travel itinerary"
```

---

## Task 7: Run full test suite + integration verify

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASSED

- [ ] **Step 2: Final commit**

```bash
git add -A && git commit -m "feat: Phase 2 complete — Two-Stage travel solver"
```

---

## Phase 2 Self-Review Checklist

| Requirement | Task | Status |
|---|---|---|
| Two-Stage architecture | Task 2-4 | ✅ |
| POI Allocator (geo+time+hotel) | Task 2-3 | ✅ |
| Travel Solver Adapter | Task 4 | ✅ |
| Budget hybrid enforcement | Task 2-3 | ✅ |
| TravelItinerary response models | Task 1 | ✅ |
| Orchestrator service | Task 5 | ✅ |
| POST /plan endpoint | Task 6 | ✅ |
| Multi-hotel support | Task 5 (_resolve_hotel) | ✅ |
| Dropped POIs tracking | Task 3, 5 | ✅ |
| Legacy endpoints untouched | All tasks | ✅ |

### Type consistency check
- `AllocationResult.day_assignments` → `Dict[int, List[str]]` ✅ used consistently
- `TravelSolverAdapter.build_problem_data()` returns `Dict` ✅ matches solver input
- `TravelPlanService.plan()` returns `TravelItinerary` ✅ matches response model
- `POI.id` type `str` ✅ used consistently across allocator and solver
