# 🗺️ AI Travel Optimizer — Routing Engine

> Hệ thống tối ưu hóa lịch trình du lịch đa ngày sử dụng thuật toán OR-Tools (CVRPTW), LLM Intent Extraction, và PostGIS Spatial Search.

---

## 📐 Kiến trúc hệ thống (System Architecture)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Mobile App (Layer 5)                         │
│              React Native / Expo — User Interface                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Layer 2 & 3 — Gateway (Orchestrator)                  │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  L2: LLM     │  │  L3: Spatial     │  │  L4 Client           │  │
│  │  Extractor   │→ │  Filter (PostGIS │→ │  (httpx → OR-Tools)  │  │
│  │  (Instructor)│  │  + pgvector)     │  │                      │  │
│  └──────────────┘  └──────────────────┘  └──────────────────────┘  │
│  FastAPI · slowapi · SQLAlchemy Async · OpenAI Embeddings           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP POST /plan
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Layer 4 — Routing Engine (OR-Tools CVRPTW)              │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  POI         │  │  Travel Solver   │  │  Distance Cache      │  │
│  │  Allocator   │→ │  (OR-Tools)      │  │  (SQLite + OSRM)     │  │
│  └──────────────┘  └──────────────────┘  └──────────────────────┘  │
│  FastAPI · asyncio.to_thread · Haversine Fallback · JIT Re-route   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP /table
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              OSRM Backend — Self-hosted Routing Server               │
│              Pre-built data: Huế (hue.osrm)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục (Directory Structure)

```
Routing Engine/
├── fleet-route-optimizer-cvrptw/    # 🧠 Layer 4: OR-Tools Routing Engine
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes.py            # POST /plan, POST /re-route, GET /health
│   │   │   └── dependencies.py      # API key verification middleware
│   │   ├── core/
│   │   │   └── solvers/
│   │   │       ├── base.py           # SolverType enum, abstract BaseSolver
│   │   │       ├── factory.py        # Solver factory pattern
│   │   │       ├── ortools_solver.py # OR-Tools solver wrapper
│   │   │       └── ortools_impl.py   # Core CVRPTW implementation (is_locked, time windows)
│   │   ├── models/
│   │   │   ├── domain.py            # POI, Hotel, DayPlan, TravelConstraints, TravelItinerary
│   │   │   └── api.py               # TravelPlanRequest, ReRouteRequest schemas
│   │   ├── services/
│   │   │   ├── travel_plan_service.py  # Main orchestrator: plan() + re_route() (JIT)
│   │   │   ├── travel_solver.py        # Solver adapter (domain → ProblemData → OR-Tools)
│   │   │   ├── poi_allocator.py        # Stage 1: POI-to-Day allocation heuristic
│   │   │   └── distance_cache.py       # SQLite cache + OSRM matrix builder
│   │   ├── config/                  # Settings, logging setup
│   │   ├── utils/                   # Haversine, helpers
│   │   └── app.py                   # FastAPI entrypoint (lifespan, CORS)
│   ├── tests/                       # 17 test files, 55+ test cases
│   │   ├── test_is_locked_poi.py    # is_locked constraint enforcement
│   │   ├── test_re_route.py         # JIT re-routing from current location
│   │   ├── test_level1_osrm_traps.py   # OSRM timeout/unreachable edge cases
│   │   ├── test_level2_ortools_traps.py # Solver edge cases (0 POIs, all locked, etc.)
│   │   ├── test_level3_system_traps.py  # Concurrency, solver-busy handling
│   │   └── ...
│   ├── Dockerfile                   # Container build
│   ├── requirements.txt             # ortools, fastapi, uvicorn, httpx
│   └── distance_cache.db            # SQLite cache (pre-populated for Huế)
│
├── layer2_3_gateway/                # 🔍 Layer 2 & 3: LLM + Spatial Gateway
│   ├── app/
│   │   ├── api/
│   │   │   └── trip_planner.py      # POST /v1/trip/plan_trip (JSON + SSE streaming)
│   │   ├── models/
│   │   │   ├── base.py              # SQLAlchemy declarative base
│   │   │   └── poi.py               # PointOfInterest ORM (PostGIS + pgvector)
│   │   ├── schemas/
│   │   │   └── trip.py              # LLMDataContract, TripPlanRequest/Response, POIResponse
│   │   ├── services/
│   │   │   ├── llm_extractor.py     # L2: AsyncOpenAI + Instructor → LLMDataContract
│   │   │   ├── spatial_filter.py    # L3: 2-phase query (Force Include + Hybrid Fill)
│   │   │   ├── embedding_service.py # OpenAI text-embedding-3-small (sync + async)
│   │   │   └── layer4_client.py     # HTTP client → Layer 4 /plan endpoint
│   │   ├── config.py                # PostgresDsn, pool sizes, rate limits, L4 URL
│   │   ├── database.py              # AsyncEngine + AsyncSessionFactory
│   │   └── main.py                  # FastAPI + ProxyHeaders + slowapi
│   ├── ingestion/
│   │   ├── ingest_pois.py           # CLI: CSV → embeddings → PostGIS batch insert
│   │   └── sample_data/             # Sample CSV datasets
│   ├── alembic/                     # Database migrations
│   ├── docker-compose.yml           # PostgreSQL + PostGIS + pgvector stack
│   ├── pyproject.toml               # Poetry dependencies
│   └── travel.env                   # Environment variables template
│
├── mobile layer/                    # 📱 Layer 5: Mobile Frontend
│   └── AITravelOptimizer/
│       ├── app/                     # Expo Router screens
│       ├── assets/                  # Icons, images
│       ├── app.config.ts            # Expo configuration
│       └── package.json             # React Native + Expo dependencies
│
├── Hue_OSRM_Data/                   # 🗺️ Pre-built OSRM graph for Huế, Vietnam
│   ├── hue.osm.pbf                  # OpenStreetMap extract
│   ├── hue.osrm                     # Compiled OSRM data
│   └── ...                          # 25 OSRM index files
│
├── pgvector/                        # 🧩 pgvector PostgreSQL extension source
├── pg_cron/                         # ⏰ pg_cron extension source (scheduled jobs)
│
├── plan/                            # 📋 Architecture & Implementation Plans
│   ├── implementation_plan.md       # Layer 4 brainstorming & architecture
│   ├── strategic-plan.md            # Overall project strategy
│   ├── phase1-*.md                  # Layer 4 domain models & API design
│   ├── phase2-*.md                  # Layer 4 allocator & solver implementation
│   ├── phase3-*.md                  # OSRM integration plans
│   ├── phase4-*.md                  # Async interface design
│   ├── layer2_3-master-design.md    # Layer 2/3 master design document
│   ├── layer2_3-v1 to v6.md        # Layer 2/3 incremental implementation plans
│   └── poi-field-extension-guide.md # Guide: adding new POI fields across layers
│
├── Embedded struture.png            # Architecture diagram (embedded view)
└── Original structure.png           # Architecture diagram (original view)
```

---

## 🧠 Chi tiết từng Layer

### Layer 4 — Routing Engine (`fleet-route-optimizer-cvrptw/`)

**Vai trò:** Bộ não toán học của hệ thống. Giải bài toán Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) để tạo ra lịch trình du lịch tối ưu.

**Công nghệ:** Google OR-Tools, FastAPI, SQLite, OSRM

| Tính năng | Trạng thái | Mô tả |
|-----------|:----------:|-------|
| Multi-day planning (`POST /plan`) | ✅ Done | Tối ưu lịch trình đa ngày, phân bổ POI theo từng ngày |
| JIT Re-routing (`POST /re-route`) | ✅ Done | Tái tính lộ trình từ vị trí GPS hiện tại (mid-trip) |
| `is_locked` constraint | ✅ Done | Ghim cứng POI bắt buộc — OR-Tools không được phép drop |
| OSRM live traffic matrix | ✅ Done | Ma trận thời gian thực từ OSRM Backend |
| Haversine fallback | ✅ Done | Khi OSRM không khả dụng, dùng công thức Haversine |
| SQLite distance cache | ✅ Done | Cache ma trận khoảng cách/thời gian theo mode (Taxi/Walking) |
| POI Allocator (Stage 1) | ✅ Done | Phân bổ POI vào từng ngày dựa trên khoảng cách + time budget |
| Budget constraint | ✅ Done | Ràng buộc ngân sách tổng (entrance fees) |
| Time window enforcement | ✅ Done | Ràng buộc giờ mở/đóng cửa của từng POI |
| Async API (non-blocking) | ✅ Done | `asyncio.to_thread` — solver chạy CPU-bound không block event loop |
| Solver-busy protection | ✅ Done | `threading.Lock` — trả HTTP 503 nếu solver đang chạy |
| Unit tests (55+ cases) | ✅ Done | Test từ unit → integration → edge cases (OSRM traps, concurrency) |

**API Endpoints:**

```
GET  /health          → {"status": "ready"} hoặc {"status": "busy"}
POST /plan            → TravelItinerary (multi-day optimized itinerary)
POST /re-route        → TravelItineraryDay (JIT single-day re-optimization)
```

---

### Layer 2 & 3 — Gateway (`layer2_3_gateway/`)

**Vai trò:** Cầu nối giữa người dùng và Routing Engine. Tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên, trích xuất ý định, tìm kiếm POI phù hợp, và gửi payload sang Layer 4.

**Công nghệ:** FastAPI, SQLAlchemy Async, PostGIS, pgvector, OpenAI (GPT-4o-mini + Embeddings), Instructor

| Tính năng | Trạng thái | Mô tả |
|-----------|:----------:|-------|
| LLM Intent Extraction (Layer 2) | ✅ Done | AsyncOpenAI + Instructor → `LLMDataContract` (Pydantic validated) |
| Force Include (`is_locked`) | ✅ Done | Phase 1 query: bypass tất cả filter, ghim cứng POI được chỉ định |
| Spatial + Semantic Search (Layer 3) | ✅ Done | PostGIS `ST_DWithin` + pgvector cosine similarity (HNSW index) |
| Multi-tier fallback | ✅ Done | 4-tier: radius expand → drop budget → drop tags → vét đáy 30km |
| POI Ingestion CLI | ✅ Done | CSV → OpenAI embeddings → PostGIS batch insert + VACUUM ANALYZE |
| Local embedding fallback | ✅ Done | sentence-transformers khi không có OpenAI API key |
| Layer 4 HTTP Client | ✅ Done | Assemble `TravelPlanRequest` → `POST /plan` qua httpx |
| SSE Streaming endpoint | ✅ Done | Real-time streaming L2→L3→L4 progress qua Server-Sent Events |
| Rate limiting | ✅ Done | slowapi — chống DDoS trên LLM/L4 endpoints |
| DB I/O isolation | ✅ Done | LLM calls chạy NGOÀI DB session → pool không bị block |
| Database migrations | ✅ Done | Alembic cho schema evolution |
| Docker Compose stack | ✅ Done | PostgreSQL 16 + PostGIS + pgvector one-command deploy |

**API Endpoints:**

```
POST /v1/trip/plan_trip          → TripPlanResponse (JSON, full pipeline)
POST /v1/trip/plan_trip_stream   → SSE stream (real-time progress)
GET  /v1/trip/health             → {"status": "ready"}
```

**Data Flow:**

```
User Prompt: "Tôi muốn đi Đại Nội Huế và Lăng Tự Đức, 2 ngày, budget 2 triệu"
  │
  ▼ Layer 2 (LLM Extractor)
  │   → LLMDataContract: {locked_pois: ["Đại Nội", "Lăng Tự Đức"], num_days: 2, budget: 2000000}
  │
  ▼ Embedding Service
  │   → query_vector: [0.12, -0.34, ...] (1536-dim)
  │
  ▼ Layer 3 (Spatial Filter)
  │   Phase 1: Force Include → 2 locked POIs (bypass all filters)
  │   Phase 2: Hybrid Fill  → 48 more POIs (PostGIS radius + pgvector cosine)
  │   → 50 POIs total
  │
  ▼ Layer 4 Client → POST /plan
  │   → TravelItinerary: {days: [{stops: [...], total_travel_min: 180}, ...]}
  │
  ▼ Response to Mobile App
```

---

### Layer 5 — Mobile App (`mobile layer/AITravelOptimizer/`)

**Vai trò:** Giao diện người dùng trên thiết bị di động.

**Công nghệ:** React Native, Expo, TypeScript

| Tính năng | Trạng thái | Mô tả |
|-----------|:----------:|-------|
| Project scaffold | ✅ Done | Expo Router + TypeScript setup |
| Screen navigation | 🔧 WIP | File-based routing via Expo Router |
| Map integration | ❌ TODO | Mapbox / Google Maps hiển thị route |
| Trip planning UI | ❌ TODO | Form nhập yêu cầu, gọi Gateway API |
| Real-time updates | ❌ TODO | SSE client nhận streaming từ Gateway |

---

### Hạ tầng (Infrastructure)

| Component | Thư mục | Mô tả |
|-----------|---------|-------|
| OSRM Data | `Hue_OSRM_Data/` | Pre-compiled routing graph cho TP Huế (OpenStreetMap) |
| pgvector | `pgvector/` | PostgreSQL extension cho vector similarity search |
| pg_cron | `pg_cron/` | PostgreSQL extension cho scheduled jobs (weather updates, etc.) |

---

## 🚀 Quick Start

### Khởi động Layer 4 (Routing Engine)

```bash
cd fleet-route-optimizer-cvrptw
pip install -r requirements.txt
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra: `curl http://localhost:8000/health`

### Khởi động Layer 2 & 3 (Gateway)

```bash
cd layer2_3_gateway

# 1. Start PostgreSQL + PostGIS + pgvector
docker-compose up -d

# 2. Run migrations
make docker-alembic-migrate

# 3. Import POI data
python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv

# 4. Start Gateway
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Chạy Test Suite (Layer 4)

```bash
cd fleet-route-optimizer-cvrptw
pytest tests/ -v
# Expected: 55/55 passed ✅
```

---

## ⚠️ Điểm cần chú ý (Important Notes)

### 1. Biến môi trường (Environment Variables)

**Layer 4** (`fleet-route-optimizer-cvrptw/.env.example`):
- `OSRM_BASE_URL` — URL của OSRM server (default: `http://localhost:5001`)
- `API_KEY` — API key cho endpoint authentication

**Layer 2 & 3** (`layer2_3_gateway/travel.env`):
- `SQL_USER`, `SQL_PASSWORD`, `SQL_HOST`, `SQL_DB` — PostgreSQL credentials
- `OPENAI_API_KEY` — Cho LLM extraction + embeddings
- `LAYER4_BASE_URL` — URL tới Layer 4 (default: `http://host.docker.internal:8000`)

### 2. OSRM Server

Layer 4 cần OSRM Backend để tính ma trận thời gian thực. Chạy Docker:

```bash
docker run -t -i -p 5001:5000 \
  -v ./Hue_OSRM_Data:/data \
  ghcr.io/project-osrm/osrm-backend:latest \
  osrm-routed --algorithm ch /data/hue.osrm
```

Nếu OSRM không khả dụng, Layer 4 tự động fallback sang Haversine distance.

### 3. is_locked — Cơ chế ghim cứng POI

Khi người dùng yêu cầu "nhất định phải đi Đại Nội Huế":
1. **Layer 2** (LLM) trích xuất tên → `locked_pois: ["Đại Nội"]`
2. **Layer 3** (PostGIS) query trực tiếp bằng tên, bypass mọi filter → `is_locked = True`
3. **Layer 4** (OR-Tools) bỏ qua `AddDisjunction` cho POI locked → không bao giờ bị drop

### 4. JIT Re-routing

Endpoint `POST /re-route` cho phép tái tính lộ trình giữa chuyến đi:
- Nhận tọa độ GPS hiện tại + thời gian hiện tại + danh sách POI còn lại
- Tạo Virtual Depot tại vị trí hiện tại
- Giải lại bài toán TSP cho phần còn lại của ngày (time_limit: 15s)

---

## 📊 Tiến độ tổng thể (Overall Progress)

| Layer | Component | Status | Tests |
|:-----:|-----------|:------:|:-----:|
| 4 | Routing Engine (OR-Tools) | ✅ Production Ready | 55/55 ✅ |
| 2 | LLM Intent Extractor | ✅ Code Complete | Manual ✅ |
| 3 | Spatial + Semantic Filter | ✅ Code Complete | Manual ✅ |
| 2&3 | Gateway Orchestrator | ✅ Code Complete | Manual ✅ |
| 5 | Mobile App | 🔧 Scaffold Only | — |
| — | OSRM Data (Huế) | ✅ Pre-built | — |
| — | PostgreSQL + pgvector | ✅ Docker Ready | — |

### TODO (Công việc cần làm tiếp)

- [ ] **Integration Test L2/3 → L4:** Viết automated test cho full pipeline
- [ ] **Mobile App UI:** Map view, trip planning form, SSE real-time updates
- [ ] **Authentication:** JWT / OAuth2 cho production deployment
- [ ] **Monitoring:** Prometheus metrics, structured logging
- [ ] **CI/CD:** GitHub Actions pipeline cho automated testing
- [ ] **Multi-city support:** Mở rộng OSRM data ngoài Huế (Đà Nẵng, Hội An, etc.)

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Solver** | Google OR-Tools (CVRPTW) |
| **Backend** | FastAPI, Uvicorn, Pydantic V2 |
| **Database** | PostgreSQL 16 + PostGIS + pgvector |
| **LLM** | OpenAI GPT-4o-mini + Instructor |
| **Embeddings** | OpenAI text-embedding-3-small (1536-dim) |
| **Routing** | OSRM (self-hosted, Contraction Hierarchies) |
| **Cache** | SQLite (distance/time matrix) |
| **Mobile** | React Native + Expo |
| **ORM** | SQLAlchemy 2.0 (async) + GeoAlchemy2 |
| **Testing** | pytest (55+ test cases) |

---

## 📄 License

MIT License — See [LICENSE](fleet-route-optimizer-cvrptw/LICENSE) for details.
