# Layer 2&3 — v1: Infrastructure (Docker + DB Init + Extensions)

> **Mục tiêu:** Build Docker image tích hợp PostGIS + pgvector + pg_cron. Tạo schema `travel` và đăng ký extensions.

## File Structure — Thay đổi

```
layer2_3_gateway/
├── db/
│   ├── Dockerfile          # MODIFY: multi-stage build PostGIS + pgvector + pg_cron
│   ├── create.sql          # MODIFY: schema travel + extensions + cron jobs
│   └── postgresql.conf     # NEW: pg_cron shared_preload_libraries
├── docker-compose.yml      # MODIFY: thêm env vars, volumes
├── farm.env → travel.env   # RENAME + MODIFY: đổi DB name
└── app/config.py           # MODIFY: thêm env vars cho LLM, Layer 4
```

---

## Task 1: Xây dựng Docker image database

**File:** `layer2_3_gateway/db/Dockerfile`

- [ ] **Step 1: Multi-stage Dockerfile kết hợp postgis + pgvector**

Thay base image `postgis/postgis:16-3.4` bằng build có pgvector:

```dockerfile
FROM postgis/postgis:16-3.4 AS base

# Install build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential postgresql-server-dev-16 git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Build pgvector from source
RUN cd /tmp && \
    git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git && \
    cd pgvector && make && make install && \
    rm -rf /tmp/pgvector

# Install pg_cron from packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-16-cron && \
    rm -rf /var/lib/apt/lists/*

# Cleanup build tools
RUN apt-get purge -y build-essential postgresql-server-dev-16 git && \
    apt-get autoremove -y

# Copy init scripts
ADD create.sql /docker-entrypoint-initdb.d/
COPY postgresql.conf /etc/postgresql/conf.d/
```

- [ ] **Step 2: Verify build**

```bash
cd layer2_3_gateway && docker build -t travel-db ./db
```

---

## Task 2: Database initialization script

**File:** `layer2_3_gateway/db/create.sql`

- [ ] **Step 1: Thay nội dung create.sql**

```sql
\connect travel;

-- Create schema
CREATE SCHEMA IF NOT EXISTS travel;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant cron usage
GRANT USAGE ON SCHEMA cron TO travel;
```

---

## Task 3: pg_cron configuration

**File:** `layer2_3_gateway/db/postgresql.conf` (NEW)

- [ ] **Step 1: Tạo file config**

```conf
shared_preload_libraries = 'pg_cron'
cron.database_name = 'travel'
```

---

## Task 4: Cập nhật docker-compose.yml

**File:** `layer2_3_gateway/docker-compose.yml`

- [ ] **Step 1: Đổi DB config từ farm → travel**

```yaml
services:
  app:
    container_name: travel-gateway
    build: .
    env_file:
      - travel.env
    command: bash -c "
      gunicorn app.main:app
      -w 4 -k uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8080
      --timeout 120
      --graceful-timeout 30
      "
    volumes:
      - ./app:/home/code/app
      - ./tests:/home/code/tests
      - ./alembic:/home/code/alembic
    ports:
      - "8080:8080"
    depends_on:
      db:
        condition: service_healthy

  db:
    container_name: travel-db
    build:
      context: ./db
      dockerfile: Dockerfile
    # CRITICAL: 4 workers × pool_max 100 = 400 connections needed.
    # PostgreSQL default max_connections = 100 → instant FATAL error.
    command: ["postgres", "-c", "max_connections=500", "-c", "shared_buffers=1GB"]
    volumes:
      - travel_data:/var/lib/postgresql/data
    ports:
      - 5432:5432
    environment:
      - POSTGRES_USER=travel
      - POSTGRES_PASSWORD=travel_secret
      - POSTGRES_DB=travel
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d travel -U travel"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  travel_data: {}
```

---

## Task 5: Cập nhật environment file

**File:** `layer2_3_gateway/travel.env` (RENAME từ farm.env)

- [ ] **Step 1: Đổi nội dung**

```env
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1

# Postgres
SQL_HOST=db
SQL_PORT=5432
SQL_DB=travel
SQL_USER=travel
SQL_PASSWORD=travel_secret

# Connection Pool (CHỐT CHẶN 4)
DB_POOL_MIN_SIZE=20
DB_POOL_MAX_SIZE=100
DB_POOL_TIMEOUT=10

# Layer 4 (OR-Tools Solver)
LAYER4_BASE_URL=http://host.docker.internal:8000

# LLM (sẽ cấu hình ở v4)
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-xxx

# Rate Limit (CHỐT CHẶN 4)
RATE_LIMIT_PER_MINUTE=5
```

---

## Verification

- [ ] `docker-compose build` thành công
- [ ] `docker-compose up db` → container healthy
- [ ] `docker exec travel-db psql -U travel -d travel -c "SELECT postgis_version();"` → trả version
- [ ] `docker exec travel-db psql -U travel -d travel -c "SELECT vector_version();"` → trả version  
- [ ] `docker exec travel-db psql -U travel -d travel -c "SELECT * FROM cron.job;"` → empty table (no error)

---

## Task 6: Infra Shield — Pool + Rate Limiter + Multi-Worker (CHỐT CHẶN 4)

> [!CAUTION]
> Thiếu 3 cơ chế bảo vệ này, hacker có thể dội bom HTTP làm nổ hóa đơn OpenAI
> và CPU Layer 4. Connection Pool không giới hạn sẽ giết PostgreSQL.

### 6a. Connection Pool Config

**File:** `layer2_3_gateway/app/config.py` — thêm vào Settings:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Connection Pool (Infra Shield)
    DB_POOL_MIN_SIZE: int = 20
    DB_POOL_MAX_SIZE: int = 100
    DB_POOL_TIMEOUT: int = 10  # seconds to wait for pool slot
    
    # Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 5
```

**File:** `layer2_3_gateway/app/database.py` — apply pool config:

```python
from app.config import settings

# AsyncSessionFactory with bounded pool
engine = create_async_engine(
    settings.database_dsn,
    pool_size=settings.DB_POOL_MIN_SIZE,
    max_overflow=settings.DB_POOL_MAX_SIZE - settings.DB_POOL_MIN_SIZE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Detect stale connections
)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)
```

### 6b. API Rate Limiter

**File:** `layer2_3_gateway/app/main.py` — thêm slowapi middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**File:** `layer2_3_gateway/app/api/trip_planner.py` — apply to endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(key_func=get_remote_address)

@router.post("/plan_trip")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip(request: Request, body: TripPlanRequest):
    ...
```

### 6c. Gunicorn Multi-Worker (docker-compose.yml)

Đã áp dụng ở Task 4: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`
- 4 workers = tận dụng tối đa CPU cores
- Mỗi worker có event loop riêng → true parallelism

**Dependencies bổ sung** (pyproject.toml):
```toml
gunicorn = "^22.0.0"
slowapi = "^0.1.9"
```
