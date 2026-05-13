# Layer 2&3 — v5: Orchestrator API + Layer 4 Integration + Tests

> **Mục tiêu:** Xây dựng API endpoint `POST /plan_trip` kết nối pipeline: Text → L2 (LLM) → L3 (Spatial Filter) → Lắp ráp `TravelPlanRequest` → L4 (OR-Tools). 
> **Phụ thuộc:** v3 (Spatial Filter) + v4 (LLM Extractor)

## File Structure — Thay đổi

```
layer2_3_gateway/app/
├── api/
│   ├── __init__.py          # KEEP
│   ├── farm.py              # DELETE
│   └── trip_planner.py      # NEW: Orchestrator routes
├── services/
│   ├── __init__.py          # MODIFY
│   ├── layer4_client.py     # NEW: HTTP client to Layer 4
│   └── embedding_service.py # NEW: Shared embedding (moved from ingestion/)
├── main.py                  # MODIFY: swap farm_router → trip_router
tests/
├── test_farm_api.py         # DELETE
└── test_trip_api.py         # NEW: integration tests
```

---

## Task 1: Layer 4 HTTP Client

**File:** `layer2_3_gateway/app/services/layer4_client.py` (NEW)

- [ ] **Step 1: HTTP client gọi sang Layer 4**

```python
"""HTTP client for Layer 4 (OR-Tools Routing Engine)."""

import httpx
from typing import Optional, Dict, List
from app.config import settings
from app.schemas.trip import POIResponse, LLMDataContract
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()


class Layer4Client:
    """Assembles TravelPlanRequest and sends to Layer 4 API."""

    def __init__(self):
        self.base_url = settings.LAYER4_BASE_URL

    def _build_payload(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
    ) -> Dict:
        """Assemble TravelPlanRequest matching Layer 4 schema exactly."""
        # Build POI list matching Layer 4's POI model
        l4_pois = []
        for p in pois:
            l4_pois.append({
                "id": str(p.uuid),
                "name": p.name,
                "category": p.category,
                "location": {"latitude": p.latitude, "longitude": p.longitude},
                "visit_duration_min": p.visit_duration_min,
                "time_window": {
                    "start_min": p.open_time,
                    "end_min": p.close_time,
                },
                "entrance_fee": p.entrance_fee,
                "priority_score": p.priority_score,
                "tags": p.tags or [],
                "description": p.description,
                "is_locked": p.is_locked,
            })

        # Build Hotel depot — one per day for multi-day trips
        # ARCHITECTURE FIX: L4 expects one hotel entry per day.
        # Hardcoding a single hotel causes IndexError on day 2+.
        hotels = []
        for day_idx in range(contract.num_days):
            hotels.append({
                "id": f"hotel_day_{day_idx}",
                "name": contract.hotel_name,
                "location": {
                    "latitude": contract.hotel_lat,
                    "longitude": contract.hotel_lon,
                },
                "assigned_days": [day_idx],
            })

        # Build Constraints
        constraints = {
            "num_days": contract.num_days,
            "budget_total": contract.budget_max,
            "transport_modes": ["taxi", "walking"],
        }

        return {
            "pois": l4_pois,
            "hotels": hotels,
            "constraints": constraints,
        }

    async def plan(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan (blocking)."""
        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/plan",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Layer 4 call failed: {e}")
            return None

    async def plan_stream(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ):
        """SSE streaming: forward Layer 4 chunks to client in real-time.

        Uses httpx async streaming to avoid buffering the entire response.
        Each chunk is yielded as an SSE event for the Mobile App.
        """
        import json as json_lib
        payload = self._build_payload(pois, contract)

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/plan",
                json=payload,
                params={"time_limit": time_limit},
            ) as response:
                response.raise_for_status()
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # Yield complete JSON lines as SSE events
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            yield f"data: {line}\n\n"
                # Flush remaining buffer
                if buffer.strip():
                    yield f"data: {buffer.strip()}\n\n"
                yield "data: [DONE]\n\n"
```

---

## Task 2: Orchestrator API Route

**File:** `layer2_3_gateway/app/api/trip_planner.py` (NEW)

- [ ] **Step 1: POST /plan_trip endpoint (JSON) + POST /plan_trip_stream endpoint (SSE)**

```python
"""Orchestrator API: Text → L2 → L3 → L4 pipeline (JSON + SSE streaming).

PRODUCTION-HARDENED ARCHITECTURE:
- DB I/O ISOLATION: LLM + Embedding calls (2-5s) execute OUTSIDE any DB session.
  DB session only opens for the 50ms spatial query then immediately returns to pool.
- ZERO Depends(get_db): Both endpoints use _run_pipeline() which owns its own session.
- Pool cannot be exhausted by LLM latency or L4 solve time under ANY load.
"""

import json as json_lib
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionFactory
from app.schemas.trip import TripPlanRequest, TripPlanResponse, LLMDataContract, POIResponse
from app.services.llm_extractor import LLMExtractorService
from app.services.spatial_filter import SpatialFilterService
from app.services.layer4_client import Layer4Client
from app.services.embedding_service import EmbeddingService
from app.utils.logging import AppLogger

# Rate limiter (initialized in main.py, imported here)
from app.main import limiter

router = APIRouter(prefix="/v1/trip")
logger = AppLogger().get_logger()

# Service singletons (stateless, thread-safe)
llm_service = LLMExtractorService()
spatial_service = SpatialFilterService()
layer4_client = Layer4Client()
embed_service = EmbeddingService()


async def _run_pipeline(
    request: TripPlanRequest,
) -> tuple[LLMDataContract, List[POIResponse]]:
    """L2 → Embed → L3 pipeline with TOTAL DB I/O isolation.

    Principle: Grab DB as LATE as possible, release as EARLY as possible.

    Timeline per request:
      [0.0s - 2.5s]  LLM intent extraction  (network I/O, NO DB)
      [2.5s - 3.0s]  Embedding generation    (network I/O, NO DB)
      [3.0s - 3.05s] Spatial query           (DB session open ~50ms)
      [3.05s+]       DB session RETURNED TO POOL
    """
    # ──── PHASE A: NETWORK I/O (NO DB SESSION) ────
    # LLM call takes 2-5s. Holding a DB session here wastes pool connections.
    contract = await llm_service.extract_intent(
        user_prompt=request.user_prompt,
        hotel_lat=request.hotel_lat,
        hotel_lon=request.hotel_lon,
        hotel_name=request.hotel_name,
        num_days=request.num_days,
    )

    query_vector = None
    if contract.tags:
        tag_text = embed_service.build_poi_text(
            name="query", category="preference",
            tags=contract.tags, description="",
        )
        try:
            query_vector = await embed_service.aembed_text(tag_text)
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to priority_score: {e}")

    # ──── PHASE B: DATABASE I/O (FLASH OPEN/CLOSE ~50ms) ────
    async with AsyncSessionFactory() as db_session:
        pois = await spatial_service.get_optimized_pois(
            contract=contract,
            db_session=db_session,
            query_vector=query_vector,
        )
    # ↑ Session RETURNED TO POOL here. DB is free for other requests.

    return contract, pois


@router.post("/plan_trip", response_model=TripPlanResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip(http_req: Request, body: TripPlanRequest):
    """Full pipeline (JSON): Text → LLM → Spatial → OR-Tools.

    Rate-limited per real client IP (via ProxyHeadersMiddleware).
    DB session lives ~50ms inside _run_pipeline(). L4 solve holds zero DB.
    """
    contract, pois = await _run_pipeline(body)

    if not pois:
        return TripPlanResponse(
            status="error", llm_contract=contract, pois_found=0,
            message="No POIs found matching your criteria.",
        )

    locked_count = sum(1 for p in pois if p.is_locked)
    l4_result = await layer4_client.plan(pois=pois, contract=contract)

    return TripPlanResponse(
        status="success" if l4_result else "partial",
        llm_contract=contract, pois_found=len(pois),
        locked_pois=locked_count, layer4_result=l4_result,
        message="Route optimized" if l4_result else "Route optimization unavailable",
    )


@router.post("/plan_trip_stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip_stream(http_req: Request, body: TripPlanRequest):
    """SSE streaming: pushes route chunks to Mobile App in real-time.

    Rate-limited per real client IP. DB session lives ~50ms.
    """
    contract, pois = await _run_pipeline(body)
    # DB already returned to pool. Streaming holds nothing.

    async def event_generator():
        yield f"data: {json_lib.dumps({'step': 'l2_done', 'tags': contract.tags, 'locked': contract.locked_pois})}\n\n"

        if not pois:
            yield f"data: {json_lib.dumps({'step': 'error', 'message': 'No POIs found'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        yield f"data: {json_lib.dumps({'step': 'l3_done', 'pois_found': len(pois), 'locked_count': sum(1 for p in pois if p.is_locked)})}\n\n"

        try:
            async for chunk in layer4_client.plan_stream(pois=pois, contract=contract):
                yield chunk
        except Exception as e:
            yield f"data: {json_lib.dumps({'step': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def health():
    return {"status": "ready", "service": "Layer 2&3 Gateway"}
```

---

## Task 3: Cập nhật main.py

**File:** `layer2_3_gateway/app/main.py`

- [ ] **Step 1: Swap router**

```python
"""FastAPI entry point — Single pool, rate limiter, proxy headers.

ARCHITECTURE:
- ONE connection pool (SQLAlchemy AsyncSessionFactory in database.py)
- NO psycopg AsyncConnectionPool (ghost pool eliminated)
- ProxyHeadersMiddleware for real client IP behind Docker NAT
- slowapi rate limiter to prevent DDoS on LLM/L4 endpoints
"""

from fastapi import FastAPI
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.trip_planner import router as trip_router
from app.config import settings

# Rate limiter singleton (imported by trip_planner.py)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Travel Gateway — Layer 2 & 3",
    version="1.0.0",
    description="LLM Intent Extraction + Spatial POI Filter + OR-Tools Integration",
)

# Decode real client IP from X-Forwarded-For (Docker NAT sends 172.x.x.x)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Wire rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(trip_router)
```

---

## Task 4: Integration Tests

**File:** `layer2_3_gateway/tests/test_trip_api.py` (NEW)

- [ ] **Step 1: Test endpoint + schema validation**

```python
"""Integration tests for trip planning API."""
import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health(client: AsyncClient):
    response = await client.get("/v1/trip/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ready"


async def test_plan_trip_validation(client: AsyncClient):
    """Test request validation."""
    response = await client.post("/v1/trip/plan_trip", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_plan_trip_minimal(client: AsyncClient):
    """Test with minimal valid request."""
    response = await client.post(
        "/v1/trip/plan_trip",
        json={
            "user_prompt": "Tôi muốn đi Huế 2 ngày",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 2,
        },
    )
    # May return partial/error if no POIs seeded, but should not crash
    assert response.status_code in [200, 404]
```

---

## Verification

- [ ] `docker-compose up` → cả app + db chạy OK
- [ ] `curl http://localhost:8080/v1/trip/health` → `{"status": "ready"}`
- [ ] Swagger UI tại `http://localhost:8080/docs` hiển thị endpoint `/v1/trip/plan_trip`
- [ ] POST `/v1/trip/plan_trip` với prompt thật → nhận response có `llm_contract` + `pois_found`
- [ ] Verify Layer 4 payload khớp schema `TravelPlanRequest` (so sánh với `fleet-route-optimizer-cvrptw/src/models/api.py`)
