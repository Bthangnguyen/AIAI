# Phase 1 (Part 2): Hotel, DayPlan & TravelConstraints Models

> Tiếp nối từ `phase1-v1`. Thêm các models: Hotel, DayPlan, TravelConstraints.

---

## Task 3: Write & Implement Hotel model

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/tests/test_travel_models.py`
- Modify: `fleet-route-optimizer-cvrptw/src/models/domain.py`

- [ ] **Step 1: Write failing tests for Hotel**

Append to `tests/test_travel_models.py`:

```python
from src.models.domain import Hotel


class TestHotelModel:
    """Test Hotel model (replaces Depot for travel)."""

    def test_hotel_basic(self):
        hotel = Hotel(
            id="hotel_001",
            name="Rex Hotel Saigon",
            location=Location(latitude=10.7769, longitude=106.7009),
            check_in_time=840,   # 14:00
            check_out_time=720,  # 12:00
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestHotelModel -v`
Expected: FAIL `ImportError: cannot import name 'Hotel'`

- [ ] **Step 3: Add Hotel model to domain.py**

Add after the POI class:

```python
class Hotel(BaseModel):
    """Hotel / accommodation — acts as depot for each day."""
    id: str = Field(..., description="Unique hotel identifier")
    name: str = Field(..., description="Hotel display name")
    location: Location = Field(..., description="Hotel coordinates")
    check_in_time: int = Field(840, description="Check-in time in minutes from midnight (default 14:00)")
    check_out_time: int = Field(720, description="Check-out time in minutes from midnight (default 12:00)")
    assigned_days: Optional[List[int]] = Field(None, description="Which day indices use this hotel as depot")
```

- [ ] **Step 4: Run tests**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestHotelModel -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/domain.py tests/test_travel_models.py
git commit -m "feat: add Hotel domain model (multi-day depot)"
```

---

## Task 4: Write & Implement DayPlan model

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/tests/test_travel_models.py`
- Modify: `fleet-route-optimizer-cvrptw/src/models/domain.py`

- [ ] **Step 1: Write failing tests for DayPlan**

Append to `tests/test_travel_models.py`:

```python
from src.models.domain import DayPlan


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
        assert plan.max_daily_minutes == 480  # 8 hours
        assert plan.max_pois == 8

    def test_dayplan_defaults(self):
        plan = DayPlan(
            day_index=1,
            date="2025-06-16",
        )
        assert plan.start_time_min == 480    # 08:00
        assert plan.end_time_min == 1260     # 21:00
        assert plan.max_daily_minutes == 600  # 10 hours
        assert plan.max_pois == 10

    def test_dayplan_with_hotel_ref(self):
        plan = DayPlan(
            day_index=0,
            date="2025-06-15",
            hotel_id="hotel_001",
        )
        assert plan.hotel_id == "hotel_001"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestDayPlanModel -v`
Expected: FAIL `ImportError: cannot import name 'DayPlan'`

- [ ] **Step 3: Add DayPlan model to domain.py**

Add after the Hotel class:

```python
class DayPlan(BaseModel):
    """A single day's plan — maps to a 'vehicle' in CVRPTW formulation.
    
    Each day has a time budget (max_daily_minutes) which acts as 'capacity',
    and each POI's visit_duration_min acts as 'demand'.
    """
    day_index: int = Field(..., description="0-based day index in the trip")
    date: str = Field(..., description="Date string YYYY-MM-DD")
    hotel_id: Optional[str] = Field(None, description="Hotel ID for this day's start/end point")
    start_time_min: int = Field(480, description="Day start time (default 08:00)")
    end_time_min: int = Field(1260, description="Day end time (default 21:00)")
    max_daily_minutes: int = Field(600, description="Max active minutes per day (default 10h)")
    max_pois: int = Field(10, description="Max number of POIs per day")
```

- [ ] **Step 4: Run tests**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestDayPlanModel -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/domain.py tests/test_travel_models.py
git commit -m "feat: add DayPlan domain model (day=vehicle mapping)"
```

---

## Task 5: Write & Implement TravelConstraints model

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/tests/test_travel_models.py`
- Modify: `fleet-route-optimizer-cvrptw/src/models/domain.py`

- [ ] **Step 1: Write failing tests for TravelConstraints**

Append to `tests/test_travel_models.py`:

```python
from src.models.domain import TravelConstraints, TransportMode


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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestTravelConstraintsModel -v`
Expected: FAIL `ImportError: cannot import name 'TravelConstraints'`

- [ ] **Step 3: Add TransportMode enum and TravelConstraints to domain.py**

Add after the DayPlan class:

```python
class TransportMode(str, Enum):
    """Supported transport modes."""
    WALKING = "walking"
    TAXI = "taxi"
    BUS = "bus"


class TravelConstraints(BaseModel):
    """Hard constraints for travel planning from the user."""
    num_days: int = Field(..., description="Number of travel days")
    budget_total: Optional[float] = Field(None, description="Total budget in VND (hard constraint)")
    transport_modes: List[TransportMode] = Field(
        default=[TransportMode.WALKING, TransportMode.TAXI, TransportMode.BUS],
        description="Allowed transport modes"
    )
    meal_break_enabled: bool = Field(False, description="Auto-insert meal breaks")
    meal_break_duration_min: int = Field(60, description="Meal break duration in minutes")
    meal_break_window: Optional[TimeWindow] = Field(
        None, description="Preferred meal time window (e.g. 11:30-13:30)"
    )
```

Note: also add `from enum import Enum` to the imports at the top of `domain.py` if not already present.

- [ ] **Step 4: Run tests**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestTravelConstraintsModel -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/domain.py tests/test_travel_models.py
git commit -m "feat: add TravelConstraints and TransportMode models"
```
