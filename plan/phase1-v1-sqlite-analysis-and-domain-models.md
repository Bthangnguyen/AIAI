# Phase 1 (Part 1): SQLite Analysis + Travel Domain Models

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform domain models from logistics (Customer/Vehicle/Depot) to travel (POI/DayPlan/Hotel) while keeping the existing Clean Architecture intact.

**Architecture:** Refactor-in-place. Replace `src/models/domain.py` with travel-specific Pydantic models. Add new `src/models/travel.py` for travel-specific types. Keep `Location`, `TimeWindow` as-is (shared primitives).

**Tech Stack:** Python 3.10+, Pydantic 2.0+, pytest

---

## SQLite vs PostgreSQL — Phân tích chi tiết

### Case A: Giữ SQLite tại Layer 4 (✅ ĐỀ XUẤT)

| Tiêu chí | Đánh giá |
|---|---|
| **Độc lập** | Layer 4 tự chứa, không phụ thuộc Layer 3 DB |
| **Tốc độ** | SQLite đọc local file, latency ~0.1ms vs PostgreSQL ~1-5ms qua network |
| **Đơn giản** | Không cần connection pool, migration, hay DB admin |
| **Cache purpose** | Distance cache là dữ liệu phái sinh (có thể rebuild từ OSRM), không cần ACID mạnh |
| **Scaling** | 50 POIs → 2500 pairs. SQLite xử lý tốt đến ~100k pairs |

### Case B: Chuyển sang PostgreSQL

| Tiêu chí | Đánh giá |
|---|---|
| **Đồng nhất** | Chung stack với Layer 3, dễ quản lý |
| **Chia sẻ** | Nhiều instance Layer 4 có thể chia sẻ cache |
| **PostGIS** | Có thể tận dụng spatial index cho distance queries |
| **Phức tạp** | Thêm dependency, cần connection string, migration |

### Case C: Hybrid (SQLite local + PostgreSQL shared)

| Tiêu chí | Đánh giá |
|---|---|
| **Hiệu quả** | SQLite làm L1 cache (hot data), PostgreSQL làm L2 (persistent) |
| **Phức tạp** | Cache invalidation giữa 2 layers |
| **Overkill** | Cho scope hiện tại (50 POIs), quá phức tạp |

### Kết luận: **Giữ SQLite (Case A)**
- Distance cache là dữ liệu phái sinh, rebuild được
- 50 POIs = 2500 pairs, SQLite xử lý dư sức
- Giữ Layer 4 độc lập, dễ test, dễ deploy
- Nếu sau này cần scale, chuyển sang PostgreSQL chỉ cần thay `DistanceCacheService` (đã tách biệt qua interface)

---

## File Structure — Những gì sẽ thay đổi

```
src/models/
├── __init__.py              # MODIFY: update exports
├── domain.py                # MODIFY: keep Location, TimeWindow; add POI, DayPlan, Hotel
├── api.py                   # MODIFY: TravelPlanRequest, TravelItinerary replaces old types
tests/
├── __init__.py              # CREATE
├── test_travel_models.py    # CREATE: tests for new domain models
```

---

## Task 1: Tạo test infrastructure

**Files:**
- Create: `fleet-route-optimizer-cvrptw/tests/__init__.py`
- Create: `fleet-route-optimizer-cvrptw/tests/test_travel_models.py`

- [ ] **Step 1: Create test directory and init file**

```python
# tests/__init__.py
```

- [ ] **Step 2: Write failing tests for POI model**

```python
# tests/test_travel_models.py
"""Tests for travel domain models."""
import pytest
from src.models.domain import Location, TimeWindow, POI


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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestPOIModel -v`
Expected: FAIL with `ImportError: cannot import name 'POI'`

- [ ] **Step 4: Commit test skeleton**

```bash
cd fleet-route-optimizer-cvrptw
git add tests/
git commit -m "test: add failing tests for POI travel domain model"
```

---

## Task 2: Implement POI model

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/src/models/domain.py`

- [ ] **Step 1: Add POI class after the existing Customer class (line ~35)**

Add this code after the `Customer` class in `domain.py`:

```python
class POI(BaseModel):
    """Point of Interest for travel itinerary."""
    id: str = Field(..., description="Unique POI identifier")
    name: str = Field(..., description="POI display name")
    category: str = Field(..., description="POI category (museum, market, park, temple, etc.)")
    location: Location = Field(..., description="POI coordinates")
    visit_duration_min: int = Field(..., description="Recommended visit duration in minutes")
    time_window: Optional[TimeWindow] = Field(None, description="Opening hours as time window")
    entrance_fee: float = Field(0.0, description="Entrance fee in VND")
    priority_score: float = Field(0.5, description="Priority score from Layer 3 (0.0-1.0)")
    tags: Optional[List[str]] = Field(None, description="Tags: outdoor, indoor, family, etc.")
    description: Optional[str] = Field(None, description="Short description")
```

- [ ] **Step 2: Run tests to verify POI tests pass**

Run: `cd fleet-route-optimizer-cvrptw && python -m pytest tests/test_travel_models.py::TestPOIModel -v`
Expected: 3 PASSED

- [ ] **Step 3: Commit**

```bash
cd fleet-route-optimizer-cvrptw
git add src/models/domain.py
git commit -m "feat: add POI domain model for travel optimization"
```
