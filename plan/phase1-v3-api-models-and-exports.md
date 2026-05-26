# Phase 1 (Part 3): API Models + Module Exports + Summary

> Tiếp nối từ `phase1-v2`. Thay đổi API request/response models và cập nhật `__init__.py`.

---

## Task 6: Write & Implement TravelPlanRequest

**Files:**
- Create: `fleet-route-optimizer-cvrptw/tests/test_api_models.py`
- Modify: `fleet-route-optimizer-cvrptw/src/models/api.py`

- [ ] **Step 1: Write failing tests for TravelPlanRequest**

```python
# tests/test_api_models.py
"""Tests for travel API request/response models."""
import pytest
from src.models.domain import Location, TimeWindow, POI, Hotel, DayPlan, TravelConstraints, TransportMode
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
        assert req.day_plans is None  # auto-generated if not provided

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
        assert total_fee > req.constraints.budget_total  # budget too small
```

- [ ] **Step 2: Run to verify failure**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_api_models.py -v`
Expected: FAIL `ImportError: cannot import name 'TravelPlanRequest'`

- [ ] **Step 3: Add TravelPlanRequest to api.py**

Replace the contents of `src/models/api.py` — keep old models but add new ones:

```python
"""API request/response models."""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from .domain import Customer, Vehicle, Depot, POI, Hotel, DayPlan, TravelConstraints


# === Legacy models (kept for backward compatibility) ===

class SolverConfig(BaseModel):
    """Solver configuration parameters."""
    time_limit: int = Field(60, description="Time limit in seconds", ge=1, le=3600)
    solver: str = Field("ortools", description="Solver type: 'ortools' or 'gurobi'")
    vehicle_penalty_weight: Optional[float] = Field(None, description="Weight for minimizing vehicles")
    distance_weight: float = Field(1.0, description="Weight for distance minimization")
    mip_gap: float = Field(0.01, description="MIP optimality gap for Gurobi")


class SolveRequest(BaseModel):
    """Legacy request to solve a CVRPTW problem."""
    date: Optional[str] = Field(None, description="Date for the problem (YYYY-MM-DD)")
    depot: Depot = Field(..., description="Depot information")
    vehicles: List[Vehicle] = Field(..., description="List of available vehicles")
    customers: List[Customer] = Field(..., description="List of customers")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")


class SolveResponse(BaseModel):
    """Legacy response containing the solution."""
    date: str = Field(..., description="Date solved for")
    summary: Dict = Field(..., description="Summary statistics")
    routes: List[Dict] = Field(..., description="Detailed routes")
    objective_value: Optional[float] = Field(None, description="Objective function value")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status: 'ready' or 'busy'")
    message: Optional[str] = Field(None, description="Additional status message")


# === New Travel API models ===

class TravelPlanRequest(BaseModel):
    """Request to create an optimized travel itinerary."""
    pois: List[POI] = Field(..., description="List of candidate POIs (max 50, pre-filtered by Layer 3)")
    hotels: List[Hotel] = Field(..., description="Hotels for each day/segment of the trip")
    constraints: TravelConstraints = Field(..., description="Hard constraints from user")
    day_plans: Optional[List[DayPlan]] = Field(None, description="Custom day plans (auto-generated if None)")
    solver_config: Optional[SolverConfig] = Field(None, description="Solver tuning parameters")
    metadata: Optional[Dict] = Field(None, description="Additional metadata from Layer 3")
```

- [ ] **Step 4: Run tests**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_api_models.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/api.py tests/test_api_models.py
git commit -m "feat: add TravelPlanRequest API model"
```

---

## Task 7: Update `__init__.py` exports

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/src/models/__init__.py`

- [ ] **Step 1: Update models __init__.py**

Replace `src/models/__init__.py` with:

```python
"""Data models for travel route optimizer."""

from .domain import (
    Location,
    TimeWindow,
    # Legacy logistics models (kept for backward compatibility)
    Customer,
    Vehicle,
    Depot,
    ProblemData,
    RouteStop,
    Route,
    Solution,
    # New travel models
    POI,
    Hotel,
    DayPlan,
    TransportMode,
    TravelConstraints,
)
from .api import (
    SolveRequest,
    SolveResponse,
    HealthResponse,
    SolverConfig,
    TravelPlanRequest,
)

__all__ = [
    # Shared primitives
    "Location",
    "TimeWindow",
    # Legacy models
    "Customer",
    "Vehicle",
    "Depot",
    "ProblemData",
    "RouteStop",
    "Route",
    "Solution",
    # Travel models
    "POI",
    "Hotel",
    "DayPlan",
    "TransportMode",
    "TravelConstraints",
    # API models
    "SolveRequest",
    "SolveResponse",
    "HealthResponse",
    "SolverConfig",
    "TravelPlanRequest",
]
```

- [ ] **Step 2: Run all tests to verify nothing is broken**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/ -v`
Expected: ALL PASSED (test_travel_models.py + test_api_models.py)

- [ ] **Step 3: Verify existing server still starts**

Run: `cd fleet-route-optimizer-cvrptw && python -c "from src.models import POI, Hotel, DayPlan, TravelConstraints, TravelPlanRequest; print('All models importable OK')"`
Expected: `All models importable OK`

- [ ] **Step 4: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/__init__.py
git commit -m "feat: export travel models from models package"
```

---

## Phase 1 Summary — Self-Review Checklist

### Spec coverage
| Requirement | Task |
|---|---|
| POI model (replaces Customer) | Task 2 ✅ |
| Hotel model (replaces Depot, multi-day) | Task 3 ✅ |
| DayPlan model (replaces Vehicle) | Task 4 ✅ |
| TravelConstraints (budget, transport, meals) | Task 5 ✅ |
| TransportMode enum (walking/taxi/bus) | Task 5 ✅ |
| TravelPlanRequest API model | Task 6 ✅ |
| Budget as hard constraint | Task 5 (budget_total field) ✅ |
| Meal breaks (optional) | Task 5 (meal_break_enabled) ✅ |
| Multi-modal transport | Task 5 (transport_modes list) ✅ |
| Multi-hotel / multi-depot | Task 3 (assigned_days) ✅ |
| Keep legacy models | Task 6-7 (backward compat) ✅ |

### What Phase 1 does NOT touch (intentionally deferred)
- ❌ Solver logic (`ortools_impl.py`) — Phase 2
- ❌ OSRM Docker setup — Phase 3
- ❌ Async interface / re-route endpoint — Phase 4
- ❌ Integration tests with real data — Phase 5

---

## Execution Options

Plan complete and saved to `plan/` directory. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
