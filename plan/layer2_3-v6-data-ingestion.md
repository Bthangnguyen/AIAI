# Layer 2&3 — v6: Data Ingestion (POI Import + OpenAI Embedding)

> **Mục tiêu:** Xây dựng module **độc lập** (standalone script, KHÔNG nằm trong Gateway) để kéo dữ liệu POI từ nguồn bên ngoài, gọi OpenAI Embedding API tạo vector 1536 chiều, rồi insert vào PostGIS.
> **Phụ thuộc:** v1 (Infrastructure) + v2 (POI table phải tồn tại)

> [!IMPORTANT]
> Module này chạy **ngoài** FastAPI Gateway. Nó là một pipeline ETL (Extract → Transform → Load) dùng để nạp dữ liệu ban đầu và cập nhật định kỳ. Không bao giờ gọi nó từ API endpoint.

## File Structure — Thêm mới

```
layer2_3_gateway/
├── app/services/
│   └── embedding_service.py  # NEW: Shared async/sync embedding (used by both Gateway & Ingestion)
├── ingestion/                    # NEW: standalone ETL module
│   ├── __init__.py               # NEW
│   ├── ingest_pois.py            # NEW: main CLI script (batch insert)
│   ├── sources/                  # NEW: data source adapters
│   │   ├── __init__.py           # NEW
│   │   ├── csv_source.py         # NEW: import từ CSV
│   │   └── google_places.py      # NEW: (future) Google Places API
│   └── sample_data/
│       └── hue_pois.csv          # NEW: sample data cho testing
├── travel.env                    # MODIFY: thêm OPENAI_API_KEY
```

> [!IMPORTANT]
> `EmbeddingService` sống trong `app/services/` (được dùng chung bởi cả Gateway và Ingestion).
> Module `ingestion/` chỉ chứa CLI scripts và source adapters.

---

## Task 1: Embedding Service (OpenAI API wrapper)

**File:** `layer2_3_gateway/app/services/embedding_service.py` (NEW — shared module)

- [ ] **Step 1: Wrapper với cả sync (cho Ingestion) và async (cho Gateway)**

```python
"""Shared embedding service for both Gateway (async) and Ingestion (sync).

Provides both sync and async methods:
- embed_text() / embed_batch() — for batch ingestion scripts
- aembed_text() — for non-blocking use inside FastAPI event loop
"""

import os
from typing import List, Optional
from openai import OpenAI, AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
EMBEDDING_DIM = 1536


class EmbeddingService:
    """Generates vector embeddings for POI text."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._sync_client = None
        self._async_client = None

    @property
    def sync_client(self) -> OpenAI:
        """Lazy-init sync client (for ingestion scripts)."""
        if self._sync_client is None:
            self._sync_client = OpenAI(api_key=self._api_key)
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy-init async client (for FastAPI Gateway)."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self._api_key)
        return self._async_client

    # --- Sync methods (Ingestion) ---

    def embed_text(self, text: str) -> List[float]:
        """Convert a single text string to 1536-dim vector (sync)."""
        response = self.sync_client.embeddings.create(
            model=EMBEDDING_MODEL, input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Batch embed multiple texts (sync). OpenAI supports up to 2048 inputs."""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.sync_client.embeddings.create(
                model=EMBEDDING_MODEL, input=batch,
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings

    # --- Async methods (Gateway) ---

    async def aembed_text(self, text: str) -> List[float]:
        """Convert text to vector (async, non-blocking for FastAPI)."""
        response = await self.async_client.embeddings.create(
            model=EMBEDDING_MODEL, input=text,
        )
        return response.data[0].embedding

    # --- Utilities ---

    @staticmethod
    def build_poi_text(name: str, category: str, tags: List[str], description: str = "") -> str:
        """Combine POI fields into a single embedding-ready text.

        Example output:
            "Đại Nội Huế | historical, culture | UNESCO World Heritage imperial citadel"
        """
        tag_str = ", ".join(tags) if tags else ""
        parts = [name, category]
        if tag_str:
            parts.append(tag_str)
        if description:
            parts.append(description)
        return " | ".join(parts)
```

---

## Task 2: CSV Source Adapter

**File:** `layer2_3_gateway/ingestion/sources/csv_source.py` (NEW)

- [ ] **Step 1: Đọc POI từ CSV file**

```python
"""Import POIs from CSV file."""

import csv
from typing import List, Dict
from pathlib import Path


def load_pois_from_csv(filepath: str) -> List[Dict]:
    """Load POI records from CSV.

    Expected columns:
        name, category, latitude, longitude, visit_duration_min,
        price, entrance_fee, open_time, close_time,
        tags (comma-separated), description, is_outdoor
    """
    pois = []
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pois.append({
                "name": row["name"].strip(),
                "category": row["category"].strip(),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "visit_duration_min": int(row.get("visit_duration_min", 60)),
                "price": float(row.get("price", 0)),
                "entrance_fee": float(row.get("entrance_fee", 0)),
                "open_time": int(row.get("open_time", 480)),
                "close_time": int(row.get("close_time", 1260)),
                "tags": [t.strip() for t in row.get("tags", "").split(",") if t.strip()],
                "description": row.get("description", ""),
                "is_outdoor": row.get("is_outdoor", "false").lower() == "true",
            })
    return pois
```

---

## Task 3: Main Ingestion Script (CLI)

**File:** `layer2_3_gateway/ingestion/ingest_pois.py` (NEW)

- [ ] **Step 1: CLI script kết nối DB → embed → batch insert**

> [!CAUTION]
> **PERFORMANCE FIX**: Dùng `executemany` batch insert thay vì vòng lặp N+1.
> Vòng lặp INSERT từng dòng tốn hàng chục phút cho 10,000+ POIs.
> Batch insert giảm xuống vài giây.

```python
"""CLI: Import POIs from CSV, generate embeddings, batch insert into PostGIS.

Usage:
    python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv

Environment:
    OPENAI_API_KEY=sk-xxx
    SQL_HOST=localhost SQL_DB=travel SQL_USER=travel SQL_PASSWORD=travel_secret
"""

import argparse
import asyncio
import os
import sys
import uuid  # CRITICAL: must generate UUID in Python for raw SQL

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import from shared module in app/services/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.embedding_service import EmbeddingService
from ingestion.sources.csv_source import load_pois_from_csv

BATCH_SIZE = 100  # rows per batch (tuned for OpenAI rate limits)

INSERT_SQL = text("""
    INSERT INTO travel.poi
        (uuid, name, category, description, coordinates,
         tags_vector, visit_duration_min, price, entrance_fee,
         open_time, close_time, tags, is_outdoor, priority_score)
    VALUES
        (:uuid, :name, :category, :description,
         ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
         CAST(:vec AS vector), :dur, :price, :fee,
         :open_t, :close_t, :tags, :outdoor, 0.5)
    ON CONFLICT ON CONSTRAINT uq_poi_name_coord DO UPDATE SET
        tags_vector = COALESCE(EXCLUDED.tags_vector, travel.poi.tags_vector),
        price = EXCLUDED.price,
        entrance_fee = EXCLUDED.entrance_fee,
        open_time = EXCLUDED.open_time,
        close_time = EXCLUDED.close_time,
        datetime_modified = NOW()
""")
# ARCHITECTURE:
# - ON CONFLICT ON CONSTRAINT uq_poi_name_coord: composite (name + coordinates)
#   Allows "Highlands Coffee" at 100 locations. Only blocks true geo-duplicates.
# - DO UPDATE SET: Upsert. Re-running CSV refreshes prices/hours without duplication.
# - COALESCE on tags_vector: Preserves existing embedding if new one is NULL.


async def _process_and_insert_batch(
    batch_rows: list,
    embed_svc: EmbeddingService,
    session: AsyncSession,
    skip_embeddings: bool,
    batch_num: int,
):
    """Process one batch: embed → build params → insert."""
    # Generate embeddings for this batch only
    embeddings = [None] * len(batch_rows)
    if not skip_embeddings:
        texts = [
            embed_svc.build_poi_text(
                r["name"], r["category"], r["tags"], r["description"]
            )
            for r in batch_rows
        ]
        embeddings = embed_svc.embed_batch(texts)

    # Build params
    params = []
    for i, poi in enumerate(batch_rows):
        params.append({
            "uuid": str(uuid.uuid4()),
            "name": poi["name"],
            "category": poi["category"],
            "description": poi["description"],
            "lon": poi["longitude"],
            "lat": poi["latitude"],
            "vec": str(embeddings[i]) if embeddings[i] else None,
            "dur": poi["visit_duration_min"],
            "price": poi["price"],
            "fee": poi["entrance_fee"],
            "open_t": poi["open_time"],
            "close_t": poi["close_time"],
            "tags": poi["tags"],
            "outdoor": poi["is_outdoor"],
        })

    await session.execute(INSERT_SQL, params)
    await session.commit()
    print(f"   Batch {batch_num}: {len(params)} rows inserted")


async def ingest(csv_path: str, skip_embeddings: bool = False):
    """Streaming ingestion pipeline (OOM-safe, rate-limit-safe).

    Architecture:
    - CSV is read row-by-row (streaming), NOT loaded entirely into RAM.
    - Each batch of BATCH_SIZE rows is embedded + inserted independently.
    - RAM usage: O(BATCH_SIZE) instead of O(total_rows).
    - 2-second sleep between embedding batches prevents OpenAI HTTP 429.
    """
    import csv as csv_mod

    db_url = (
        f"postgresql+psycopg://{os.getenv('SQL_USER', 'travel')}"
        f":{os.getenv('SQL_PASSWORD', 'travel_secret')}"
        f"@{os.getenv('SQL_HOST', 'localhost')}"
        f"/{os.getenv('SQL_DB', 'travel')}"
    )
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    embed_svc = EmbeddingService()

    print(f"🚀 Stream processing {csv_path} (batch_size={BATCH_SIZE})...")
    total_inserted = 0
    batch_num = 0
    batch = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            poi = {
                "name": row["name"].strip(),
                "category": row["category"].strip(),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "visit_duration_min": int(row.get("visit_duration_min", 60)),
                "price": float(row.get("price", 0)),
                "entrance_fee": float(row.get("entrance_fee", 0)),
                "open_time": int(row.get("open_time", 480)),
                "close_time": int(row.get("close_time", 1260)),
                "tags": [t.strip() for t in row.get("tags", "").split(",") if t.strip()],
                "description": row.get("description", ""),
                "is_outdoor": row.get("is_outdoor", "false").lower() == "true",
            }
            batch.append(poi)

            if len(batch) >= BATCH_SIZE:
                batch_num += 1
                async with async_session() as session:
                    await _process_and_insert_batch(
                        batch, embed_svc, session, skip_embeddings, batch_num
                    )
                total_inserted += len(batch)
                batch.clear()  # Free RAM immediately

                if not skip_embeddings:
                    await asyncio.sleep(2)  # Rate limit protection: 2s cooldown

        # Flush remaining rows
        if batch:
            batch_num += 1
            async with async_session() as session:
                await _process_and_insert_batch(
                    batch, embed_svc, session, skip_embeddings, batch_num
                )
            total_inserted += len(batch)

    await engine.dispose()
    print(f"✅ Done! Inserted {total_inserted} POIs in {batch_num} batches")

    # POST-INGESTION: Reclaim dead tuples + rebuild index statistics
    # Upsert (DO UPDATE SET) creates massive MVCC bloat.
    # Without VACUUM, HNSW index scan degrades from ~10ms to ~seconds.
    # VACUUM cannot run inside a transaction block → use autocommit.
    print("🧹 Running VACUUM ANALYZE on travel.poi (reclaiming MVCC dead tuples)...")
    import psycopg
    conninfo = (
        f"postgresql://{os.getenv('SQL_USER', 'travel')}"
        f":{os.getenv('SQL_PASSWORD', 'travel_secret')}"
        f"@{os.getenv('SQL_HOST', 'localhost')}"
        f"/{os.getenv('SQL_DB', 'travel')}"
    )
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("VACUUM ANALYZE travel.poi;")
    print("✨ Database optimized. HNSW index at peak performance.")


def main():
    parser = argparse.ArgumentParser(description="Import POIs into PostGIS")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip OpenAI embedding generation")
    args = parser.parse_args()

    asyncio.run(ingest(args.csv, args.skip_embeddings))


if __name__ == "__main__":
    main()
```

---

## Task 4: Sample Data

**File:** `layer2_3_gateway/ingestion/sample_data/hue_pois.csv` (NEW)

- [ ] **Step 1: Tạo sample CSV cho thành phố Huế**

```csv
name,category,latitude,longitude,visit_duration_min,price,entrance_fee,open_time,close_time,tags,description,is_outdoor
Đại Nội Huế,historical,16.4698,107.5786,120,0,200000,420,1020,"culture,heritage,UNESCO",Imperial Citadel of Hue - UNESCO World Heritage,false
Chùa Thiên Mụ,temple,16.4538,107.5466,60,0,0,360,1080,"temple,spiritual,panorama",Iconic 7-story pagoda on Perfume River,true
Lăng Tự Đức,historical,16.4575,107.5668,90,0,150000,420,1020,"culture,heritage,tomb",Tomb of Emperor Tu Duc in lush gardens,true
Chợ Đông Ba,market,16.4687,107.5851,60,0,0,300,1140,"market,street_food,shopping",Largest market in Hue for local goods,false
Cầu Trường Tiền,landmark,16.4691,107.5801,30,0,0,0,1440,"landmark,photo,riverside",Historic bridge spanning Perfume River,true
Bún Bò Huế Bà Tuyết,restaurant,16.4629,107.5893,45,50000,0,360,1260,"street_food,local,spicy",Famous Bun Bo Hue noodle shop,false
Lăng Khải Định,historical,16.4062,107.5994,90,0,150000,420,1020,"culture,heritage,art_deco",Ornate tomb with mosaic decorations,false
Biển Thuận An,beach,16.5437,107.6312,180,0,0,360,1080,"beach,nature,swimming",Nearest beach to Hue city center,true
Sông Hương Boat Tour,tour,16.4590,107.5770,120,200000,0,480,1020,"river,scenic,boat",Sunset dragon boat cruise on Perfume River,true
Núi Ngự Bình,nature,16.4365,107.5878,150,0,0,360,1080,"hiking,nature,panorama",Mountain hike with panoramic city views,true
```

---

## Verification

- [ ] `python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv --skip-embeddings` → Insert 10 POIs without calling OpenAI
- [ ] `docker exec travel-db psql -U travel -d travel -c "SELECT name, category FROM travel.poi;"` → 10 rows
- [ ] `python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv` → (with OPENAI_API_KEY set) Insert + generate embeddings
- [ ] `docker exec travel-db psql -U travel -d travel -c "SELECT name, tags_vector IS NOT NULL as has_vector FROM travel.poi;"` → all `has_vector = true`
- [ ] End-to-end: sau khi ingest → gọi `POST /plan_trip` → verify spatial filter trả về POIs đã nạp

---

## Lưu ý Kiến trúc

> [!WARNING]
> **Module này KHÔNG import từ `app/`**. Nó có dependency riêng (`openai`, `sqlalchemy`) và kết nối trực tiếp tới database. Lý do:
> - Tách biệt luồng ingestion (batch, offline) và luồng serving (real-time, online)
> - Có thể chạy trên máy khác hoặc trong CI/CD pipeline
> - Không ảnh hưởng đến performance của Gateway khi nạp hàng ngàn POIs

> [!TIP]
> **Mở rộng trong tương lai:**
> - `sources/google_places.py`: Kéo POI từ Google Places API
> - `sources/tripadvisor.py`: Crawl rating/review data
> - Chạy định kỳ qua `pg_cron` hoặc Airflow/Prefect
