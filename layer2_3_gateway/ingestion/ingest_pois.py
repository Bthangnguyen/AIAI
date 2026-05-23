"""CLI: Import POIs from CSV, generate embeddings, batch insert into PostGIS.

Usage:
    python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv
    python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv --skip-embeddings

Environment:
    SQL_USER, SQL_PASSWORD, SQL_HOST, SQL_DB (from travel.env)
    OPENAI_API_KEY (optional — falls back to local sentence-transformers)
"""

import argparse
import asyncio
import csv as csv_mod
import os
import sys
import uuid

# Setup Windows asyncio policy for psycopg compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent dir so we can import from app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.embedding_service import EmbeddingService

BATCH_SIZE = 100

INSERT_SQL = text("""
    INSERT INTO travel.poi
        (uuid, name, category, description, coordinates,
         tags_vector, visit_duration_min, price, entrance_fee,
         open_time, close_time, tags, is_outdoor, priority_score,
         weather_penalty, datetime_created, datetime_modified)
    VALUES
        (:uuid, :name, :category, :description,
         ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
         CAST(:vec AS vector), :dur, :price, :fee,
         :open_t, :close_t, CAST(:tags AS text[]), :outdoor, :priority,
         0.0, NOW(), NOW())
    ON CONFLICT ON CONSTRAINT uq_poi_name_coord DO UPDATE SET
        tags_vector = COALESCE(EXCLUDED.tags_vector, travel.poi.tags_vector),
        price = EXCLUDED.price,
        entrance_fee = EXCLUDED.entrance_fee,
        open_time = EXCLUDED.open_time,
        close_time = EXCLUDED.close_time,
        priority_score = EXCLUDED.priority_score,
        datetime_modified = NOW()
""")


def _build_local_embeddings(texts: list) -> list:
    """Generate embeddings locally using sentence-transformers.

    Falls back to this when OpenAI API Key is unavailable.
    Uses all-MiniLM-L6-v2 (384-dim) and pads to 1536-dim for pgvector compatibility.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("⚠️  sentence-transformers not installed. Run: pip install sentence-transformers")
        return [None] * len(texts)

    print("   Using local sentence-transformers (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    raw_embeddings = model.encode(texts, show_progress_bar=True)

    # Pad from 384 → 1536 dimensions to match pgvector column
    padded = []
    for emb in raw_embeddings:
        padded_emb = np.zeros(1536)
        padded_emb[:384] = emb
        padded.append(padded_emb.tolist())

    return padded


def _compute_priority(poi: dict) -> float:
    """Compute a basic priority_score based on POI attributes.

    Instead of all 0.50, differentiate POIs so ORDER BY works meaningfully.
    Score range: 0.0 - 1.0
    """
    score = 0.5  # base

    # UNESCO / major landmarks get a boost
    tags = poi.get("tags", [])
    if "UNESCO" in tags or "heritage" in tags:
        score += 0.15
    if "culture" in tags:
        score += 0.05

    # Free entry is more accessible
    if poi.get("entrance_fee", 0) == 0:
        score += 0.05

    # Longer visits = more substantial attraction
    dur = poi.get("visit_duration_min", 60)
    if dur >= 120:
        score += 0.10
    elif dur >= 60:
        score += 0.05

    # Street food is popular
    if "street_food" in tags:
        score += 0.08

    # Nature attractions
    if "nature" in tags or "hiking" in tags:
        score += 0.05

    return min(score, 1.0)


async def _process_and_insert_batch(
    batch_rows: list,
    embed_svc: EmbeddingService,
    session: AsyncSession,
    skip_embeddings: bool,
    use_local_embed: bool,
    batch_num: int,
):
    """Process one batch: embed → build params → insert."""
    embeddings = [None] * len(batch_rows)

    if not skip_embeddings:
        texts = [
            embed_svc.build_poi_text(
                r["name"], r["category"], r["tags"], r["description"]
            )
            for r in batch_rows
        ]

        if use_local_embed:
            embeddings = _build_local_embeddings(texts)
        else:
            try:
                embeddings = embed_svc.embed_batch(texts)
            except Exception as e:
                print(f"   ⚠️  OpenAI embed failed: {e}. Trying local fallback...")
                embeddings = _build_local_embeddings(texts)

    # Build params
    params = []
    for i, poi in enumerate(batch_rows):
        tags_str = "{" + ",".join(f'"{t}"' for t in poi["tags"]) + "}"
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
            "tags": tags_str,
            "outdoor": poi["is_outdoor"],
            "priority": _compute_priority(poi),
        })

    # executemany via execute with list of dicts
    for p in params:
        await session.execute(INSERT_SQL, p)
    await session.commit()
    print(f"   Batch {batch_num}: {len(params)} rows inserted/updated")


async def ingest(csv_path: str, skip_embeddings: bool = False, use_local_embed: bool = False):
    """Streaming ingestion pipeline."""
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
                        batch, embed_svc, session, skip_embeddings, use_local_embed, batch_num
                    )
                total_inserted += len(batch)
                batch.clear()

                if not skip_embeddings:
                    await asyncio.sleep(2)

        # Flush remaining rows
        if batch:
            batch_num += 1
            async with async_session() as session:
                await _process_and_insert_batch(
                    batch, embed_svc, session, skip_embeddings, use_local_embed, batch_num
                )
            total_inserted += len(batch)

    await engine.dispose()
    print(f"✅ Done! Inserted/Updated {total_inserted} POIs in {batch_num} batches")

    # POST-INGESTION: VACUUM ANALYZE
    print("🧹 Running VACUUM ANALYZE on travel.poi...")
    import psycopg
    conninfo = (
        f"postgresql://{os.getenv('SQL_USER', 'travel')}"
        f":{os.getenv('SQL_PASSWORD', 'travel_secret')}"
        f"@{os.getenv('SQL_HOST', 'localhost')}"
        f"/{os.getenv('SQL_DB', 'travel')}"
    )
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("VACUUM ANALYZE travel.poi;")
    print("✨ Database optimized.")


def main():
    parser = argparse.ArgumentParser(description="Import POIs into PostGIS")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip all embedding generation")
    parser.add_argument("--local-embed", action="store_true",
                        help="Use local sentence-transformers instead of OpenAI")
    args = parser.parse_args()

    asyncio.run(ingest(args.csv, args.skip_embeddings, args.local_embed))


if __name__ == "__main__":
    main()
