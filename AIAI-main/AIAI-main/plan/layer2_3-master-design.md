# Layer 2 & 3 — Master Design: Phân tích 3 Repo & Ánh xạ Embedded Structure

## 1. Tổng quan hệ thống nhúng (Embedded Structure)

```
Routing Engine/
├── fleet-route-optimizer-cvrptw/   ← Layer 4 (OR-Tools Solver) ✅ DONE
├── layer2_3_gateway/               ← fastapi-postgis (Khung sườn Layer 2&3)
├── pgvector/                       ← PostgreSQL extension (Semantic Search)
└── pg_cron/                        ← PostgreSQL extension (Scheduled Jobs)
```

### Luồng dữ liệu End-to-End
```
Client (text) → Orchestrator → Layer 2 (LLM) → JSON Contract
                             → Layer 3 (PostGIS+pgvector) → 50 POIs
                             → Layer 4 (OR-Tools) POST /plan → TravelItinerary
```

---

## 2. Phân tích chi tiết 3 Repo

### 2.1 `fastapi-postgis` — Khung sườn ứng dụng

| Thành phần | File gốc | Vai trò | Giữ/Đổi |
|---|---|---|---|
| **FastAPI app** | `app/main.py` | Entry point, `ProxyHeadersMiddleware` + `slowapi` rate limiter | ✅ Đổi: xóa psycopg pool, thêm infra shield |
| **Config** | `app/config.py` | Pydantic `BaseSettings`, pool config, rate limit config | ✅ Thêm `DB_POOL_*`, `RATE_LIMIT_PER_MINUTE` |
| **Database** | `app/database.py` | `create_async_engine` (bounded pool) + `AsyncSessionFactory` | ✅ Single pool, no DI `get_db()` on endpoints |
| **Base Model** | `app/models/base.py` | `DeclarativeBase` + `save_and_refresh()` helper | ✅ Giữ nguyên |
| **ORM Model** | `app/models/farm.py` | `FarmField`: Geometry(POLYGON), ST_Area, get_farm_fields() | 🔄 Đổi → `POI`: Geometry(POINT) |
| **Schema** | `app/schemas/farm.py` | Pydantic `FarmField` + `FarmFieldResponse` + geojson_pydantic | 🔄 Đổi → Trip schemas |
| **API Route** | `app/api/farm.py` | POST create + GET by UUID, dùng `psycopg` raw SQL | 🔄 Đổi → Trip planner routes |
| **Utils** | `app/utils/` | Singleton + Rich logging | ✅ Giữ nguyên |
| **Alembic** | `alembic/` | Async migrations, GeoAlchemy2 helpers, schema `coffee` | 🔄 Đổi schema → `travel` |
| **Docker** | `docker-compose.yml` | PostGIS 16 + FastAPI app | 🔄 Mở rộng thêm pgvector+pg_cron |
| **DB Init** | `db/create.sql` | `CREATE SCHEMA coffee;` | 🔄 Đổi → travel schema + extensions |
| **Tests** | `tests/` | pytest + httpx AsyncClient + inline_snapshot | ✅ Giữ pattern, đổi test cases |

**Kết luận**: Repo này cung cấp 100% hạ tầng cần thiết (async DB, migrations, Docker, testing). Chỉ cần thay domain `Farm` → `Travel`.

### 2.2 `pgvector` — Vector Similarity Search

| Khả năng | Chi tiết | Ứng dụng trong Layer 3 |
|---|---|---|
| **Kiểu dữ liệu** | `vector(N)` — lưu embedding N chiều | Lưu `tags_vector` cho mỗi POI |
| **Toán tử** | `<->` L2, `<=>` Cosine, `<#>` Inner Product | Tính similarity giữa sở thích khách & POI |
| **Index HNSW** | Approximate NN, tốc độ cao | Index cho 3000+ POIs |
| **Filtering** | `WHERE ... ORDER BY vec <-> query LIMIT N` | Kết hợp hard filter + soft rank |
| **Docker** | Dockerfile build pgvector vào postgres:17 | Tích hợp vào `db/Dockerfile` |

**Cách tích hợp**: Merge Dockerfile pgvector vào `db/Dockerfile` của fastapi-postgis (thay base image `postgis/postgis:16` bằng multi-stage build có pgvector).

### 2.3 `pg_cron` — Database Job Scheduler

| Khả năng | Chi tiết | Ứng dụng trong Layer 3 |
|---|---|---|
| **Schedule** | Cron syntax + interval (seconds) | Weather penalty update mỗi 5 phút |
| **API** | `cron.schedule(name, schedule, command)` | Đăng ký job trong `db/create.sql` |
| **Monitoring** | `cron.job_run_details` table | Debug weather updates |
| **Cài đặt** | `shared_preload_libraries = 'pg_cron'` | Thêm vào `db/postgresql.conf` |

**Cách tích hợp**: Cài pg_cron vào Docker image, thêm config vào `postgresql.conf`, đăng ký cron job trong `create.sql`.

---

## 3. Ánh xạ (Mapping) vào Embedded Structure

### 3.1 Farm → Travel Domain Mapping

| Farm (Gốc) | Travel (Mới) | Ghi chú |
|---|---|---|
| `FarmField` ORM | `PointOfInterest` ORM | POLYGON → POINT, thêm vector column |
| `FarmField` Schema | `LLMDataContract` + `POIResponse` | Input từ LLM + Output cho L4 |
| `farm.py` API | `trip_planner.py` API | POST /plan_trip endpoint |
| Schema `coffee` | Schema `travel` | Database namespace |
| `ST_Area`, `ST_Perimeter` | `ST_DWithin`, `<->` operator | Spatial functions |

### 3.2 Layer 4 Handoff Interface (Đã hoàn thành)

Layer 3 output phải khớp chính xác với `TravelPlanRequest`:
```python
# Layer 4 expects (from fleet-route-optimizer-cvrptw/src/models/api.py):
class TravelPlanRequest:
    pois: List[POI]              # ≤ 50 POIs, mỗi POI có is_locked
    hotels: List[Hotel]          # Depot cho mỗi ngày
    constraints: TravelConstraints  # num_days, budget, transport_modes
    day_plans: Optional[List[DayPlan]]
    solver_config: Optional[SolverConfig]

# Layer 4 API (from routes.py):
POST /plan  → TravelItinerary
POST /re-route → TravelItineraryDay
```

---

## 4. Kế hoạch xây dựng — Chia thành 6 phiên bản

| Version | Tên | Mô tả | Dependencies |
|---|---|---|---|
| **v1** | Infrastructure | Docker image (PostGIS+pgvector+pg_cron), DB init, config | Không |
| **v2** | Domain Models | POI ORM + **HNSW Index** + Pydantic schemas + Alembic migration | v1 |
| **v3** | Layer 3 Filter | Spatial filter: Force Include + Hybrid Search + Fallback | v2 |
| **v4** | Layer 2 LLM | Intent extraction: Text → LLMDataContract (Instructor) | v1 |
| **v5** | Orchestrator | API endpoint (JSON + **SSE Streaming**) + L2→L3→L4 pipeline | v3, v4 |
| **v6** | Data Ingestion | **Standalone** ETL: CSV → OpenAI Embedding → PostGIS insert | v1, v2 |

### Dependency Graph

```
v1 (Infra) ──→ v2 (Models+HNSW) ──→ v3 (L3 Filter) ─┐
    │                │                                  ├→ v5 (Orchestrator+SSE)
    │                └──→ v6 (Data Ingestion)           │
    └──→ v4 (L2 LLM) ─────────────────────────────────┘
```

> **Parallelism:** v3, v4, v6 có thể chạy song song sau khi v2 hoàn thành.

Chi tiết từng version xem file tương ứng: `layer2_3-v1-*.md` ... `layer2_3-v6-*.md`

