# Layer 2&3 — v2: Domain Models (POI ORM + Schemas + Migration)

> **Mục tiêu:** Chuyển đổi domain `FarmField` → `PointOfInterest` ORM model. Tạo Pydantic schemas cho Layer 2 output và Layer 4 input. Chạy Alembic migration.
> **Phụ thuộc:** v1 (Infrastructure)

## File Structure — Thay đổi

```
layer2_3_gateway/app/
├── models/
│   ├── __init__.py         # MODIFY: import POI thay vì FarmField
│   ├── base.py             # KEEP: DeclarativeBase + save_and_refresh
│   ├── farm.py             # DELETE
│   └── poi.py              # NEW: PointOfInterest ORM (PostGIS + pgvector)
├── schemas/
│   ├── __init__.py         # KEEP
│   ├── farm.py             # DELETE
│   └── trip.py             # NEW: LLMDataContract + POIResponse + TravelPlanPayload
alembic/env.py              # MODIFY: schema coffee → travel
tests/
├── test_farm_api.py        # DELETE
└── test_poi_models.py      # NEW: unit tests cho POI model
```

---

## Task 1: Tạo POI ORM Model

**File:** `layer2_3_gateway/app/models/poi.py` (NEW)

- [ ] **Step 1: Định nghĩa model kế thừa pattern từ FarmField**

```python
"""POI (Point of Interest) ORM model for Layer 3 spatial database."""

import uuid
from datetime import datetime
from typing import Any, Optional, List

from geoalchemy2.types import Geography  # NOT Geometry — measures in meters natively
from geoalchemy2.functions import ST_AsGeoJSON, ST_DWithin, ST_MakePoint
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Boolean, Text, Index,
    UniqueConstraint, select, func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PointOfInterest(Base):
    """POI stored in PostGIS with vector embeddings for semantic search."""

    __tablename__ = "poi"
    __table_args__ = (
        # HNSW index for pgvector semantic similarity (cosine distance)
        Index(
            "idx_poi_tags_vector",
            "tags_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"tags_vector": "vector_cosine_ops"},
        ),
        # GiST spatial index for PostGIS ST_DWithin queries
        Index(
            "idx_poi_coordinates",
            "coordinates",
            postgresql_using="gist",
        ),
        # B-tree indexes for hard constraint filters
        Index("idx_poi_price", "price"),
        Index("idx_poi_weather_penalty", "weather_penalty"),
        # Composite unique: same name at same location = duplicate
        # Allows "Highlands Coffee" at 100 different coordinates
        UniqueConstraint("name", "coordinates", name="uq_poi_name_coord"),
        {"schema": "travel"},
    )

    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # GeoAlchemy2: POINT(lon, lat) in SRID 4326 — Geography type
    # Geography measures distance in METERS natively.
    # GiST index on Geography column is used by ST_DWithin WITHOUT casting.
    # Using Geometry here would require cast() at query time → kills index.
    coordinates = Column(Geography("POINT", srid=4326), nullable=False)

    # pgvector: embedding for semantic similarity search
    tags_vector = Column(Vector(1536), nullable=True)

    # Travel attributes
    visit_duration_min: Mapped[int] = mapped_column(Integer, default=60)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    entrance_fee: Mapped[float] = mapped_column(Float, default=0.0)
    open_time: Mapped[int] = mapped_column(Integer, default=480)   # 08:00
    close_time: Mapped[int] = mapped_column(Integer, default=1260) # 21:00
    priority_score: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Weather & outdoor
    is_outdoor: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_penalty: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    datetime_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    datetime_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    @classmethod
    async def search_within_radius(
        cls,
        lat: float, lon: float, radius_m: float,
        extra_conditions: list[Any] = None,
        limit: int = 50,
        database_session: Optional[AsyncSession] = None,
    ):
        """Spatial search: find POIs within radius, ordered by distance."""
        center = func.ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        conditions = [ST_DWithin(cls.coordinates, center, radius_m, use_spheroid=True)]
        if extra_conditions:
            conditions.extend(extra_conditions)

        _stmt = select(
            cls.uuid, cls.name, cls.category, cls.description,
            cls.visit_duration_min, cls.price, cls.entrance_fee,
            cls.open_time, cls.close_time, cls.priority_score,
            cls.tags, cls.is_outdoor, cls.weather_penalty,
            ST_AsGeoJSON(cls.coordinates).label("geojson_coordinates"),
        ).where(*conditions).limit(limit)

        _result = await database_session.execute(_stmt)
        return _result.fetchall()
```

---

## Task 2: Tạo Pydantic Schemas

**File:** `layer2_3_gateway/app/schemas/trip.py` (NEW)

- [ ] **Step 1: Định nghĩa schemas**

```python
"""Pydantic schemas bridging Layer 2 (LLM) → Layer 3 (DB) → Layer 4 (Solver)."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from geojson_pydantic import Point
from pydantic import BaseModel, Field, ConfigDict


# === Layer 2 Output: LLM extracts this from user text ===

class TimeWindowSpec(BaseModel):
    start_min: int = Field(480, description="Start time in minutes from midnight")
    end_min: int = Field(1260, description="End time in minutes from midnight")


class LLMDataContract(BaseModel):
    """JSON contract produced by Layer 2 (LLM intent extraction)."""
    budget_max: Optional[float] = Field(None, description="Max budget in VND")
    radius_km: float = Field(10.0, description="Search radius from hotel in km")
    num_days: int = Field(1, description="Number of travel days")
    time_window: Optional[TimeWindowSpec] = None
    tags: List[str] = Field(default_factory=list, description="Preference tags")
    locked_pois: List[str] = Field(default_factory=list, description="Must-visit POI names")
    weather_preference: Optional[str] = Field(None, description="indoor/outdoor/any")
    hotel_lat: float = Field(..., description="Hotel latitude")
    hotel_lon: float = Field(..., description="Hotel longitude")
    hotel_name: str = Field("Hotel", description="Hotel display name")


# === Layer 3 Output: POI returned from spatial filter ===

class POIResponse(BaseModel):
    """Single POI result from Layer 3 spatial filter."""
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    category: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    visit_duration_min: int = 60
    price: float = 0.0
    entrance_fee: float = 0.0
    open_time: int = 480
    close_time: int = 1260
    priority_score: float = 0.5
    tags: Optional[List[str]] = None
    is_locked: bool = False


# === Orchestrator Output: Assembled for Layer 4 ===

class TripPlanRequest(BaseModel):
    """User-facing request: just send text + hotel info."""
    user_prompt: str = Field(..., description="Natural language travel request")
    hotel_lat: float = Field(..., description="Hotel latitude")
    hotel_lon: float = Field(..., description="Hotel longitude")
    hotel_name: str = Field("Hotel", description="Hotel name")
    num_days: int = Field(1, description="Number of travel days")


class TripPlanResponse(BaseModel):
    """Response from orchestrator (wraps Layer 4 output)."""
    status: str = "success"
    llm_contract: Optional[LLMDataContract] = None
    pois_found: int = 0
    locked_pois: int = 0
    layer4_result: Optional[dict] = None
    message: Optional[str] = None
```

---

## Task 3: Cập nhật models/__init__.py và alembic

**File:** `layer2_3_gateway/app/models/__init__.py`

- [ ] **Step 1: Đổi import**

```python
# for Alembic and unit tests
from app.models.poi import *  # noqa
```

**File:** `layer2_3_gateway/alembic/env.py`

- [ ] **Step 2: Đổi schema name trong include_name**

```python
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in ["travel"]
    else:
        return True
```

---

## Task 4: Viết unit tests

**File:** `layer2_3_gateway/tests/test_poi_models.py` (NEW)

- [ ] **Step 1: Test POI schema validation**

```python
import pytest
from app.schemas.trip import LLMDataContract, POIResponse, TripPlanRequest

def test_llm_data_contract_defaults():
    c = LLMDataContract(hotel_lat=16.46, hotel_lon=107.59)
    assert c.radius_km == 10.0
    assert c.num_days == 1
    assert c.tags == []
    assert c.locked_pois == []

def test_llm_data_contract_full():
    c = LLMDataContract(
        budget_max=2000000, radius_km=15, num_days=3,
        tags=["culture", "street_food"],
        locked_pois=["Đại Nội Huế", "Lăng Tự Đức"],
        weather_preference="indoor",
        hotel_lat=16.4637, hotel_lon=107.5905,
    )
    assert len(c.locked_pois) == 2
    assert c.budget_max == 2000000

def test_trip_plan_request_required_fields():
    r = TripPlanRequest(
        user_prompt="Tôi muốn đi Huế 3 ngày",
        hotel_lat=16.46, hotel_lon=107.59, num_days=3,
    )
    assert r.num_days == 3
```

---

## Verification

- [ ] `python -m pytest tests/test_poi_models.py -v` → ALL PASSED
- [ ] `alembic revision --autogenerate -m "create poi table"` → migration file created
- [ ] `alembic upgrade head` → table `travel.poi` created in DB
- [ ] `docker exec travel-db psql -U travel -d travel -c "\dt travel.*"` → shows `poi` table
