"""Backfill normalized POI tags and pgvector embeddings.

Usage from layer2_3_gateway:
    python scripts/backfill_poi_semantics.py --dry-run --limit 10
    python scripts/backfill_poi_semantics.py
    python scripts/backfill_poi_semantics.py --skip-embeddings
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.embedding_service import EmbeddingService
from app.services.poi_tag_normalizer import build_embedding_text, normalize_tags


BATCH_SIZE = 50


def conninfo() -> str:
    host = os.getenv("SQL_HOST", "localhost")
    if host == "db":
        host = "localhost"
    return (
        f"dbname={os.getenv('SQL_DB', 'travel')} "
        f"user={os.getenv('SQL_USER', 'travel')} "
        f"password={os.getenv('SQL_PASSWORD', 'travel_secret')} "
        f"host={host} "
        f"port={os.getenv('SQL_PORT', '5432')}"
    )


def _vector_literal(vector: list[float] | None) -> str | None:
    return str(vector) if vector else None


def fetch_rows(limit: int | None) -> list[dict]:
    sql = """
        SELECT uuid::text, name, category, category_group, description, tags
        FROM travel.poi
        ORDER BY category_group, name
    """
    if limit:
        sql += " LIMIT %s"
    with psycopg.connect(conninfo()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,) if limit else None)
            cols = [desc.name for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def update_rows(rows: list[dict], embeddings: list[list[float] | None], dry_run: bool) -> None:
    if dry_run:
        for row, emb in zip(rows[:10], embeddings[:10]):
            print(f"- {row['name']} [{row.get('category_group')}] tags={row['normalized_tags']} vec={bool(emb)}")
        return

    sql = """
        UPDATE travel.poi
        SET tags = %s,
            tags_vector = COALESCE(CAST(%s AS vector), tags_vector),
            datetime_modified = NOW()
        WHERE uuid = %s::uuid
    """
    with psycopg.connect(conninfo()) as conn:
        with conn.cursor() as cur:
            for row, emb in zip(rows, embeddings):
                cur.execute(sql, (row["normalized_tags"], _vector_literal(emb), row["uuid"]))
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize POI tags and backfill embeddings")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    rows = fetch_rows(args.limit)
    print(f"Loaded {len(rows)} POIs")

    texts: list[str] = []
    for row in rows:
        tags = normalize_tags(
            name=row["name"],
            category=row.get("category"),
            category_group=row.get("category_group"),
            description=row.get("description"),
            raw_tags=row.get("tags"),
        )
        row["normalized_tags"] = tags
        texts.append(build_embedding_text(
            name=row["name"],
            category=row.get("category"),
            category_group=row.get("category_group"),
            description=row.get("description"),
            tags=tags,
        ))

    embeddings: list[list[float] | None] = [None] * len(rows)
    if not args.skip_embeddings:
        embedder = EmbeddingService()
        embeddings = []
        for idx in range(0, len(texts), BATCH_SIZE):
            batch = texts[idx:idx + BATCH_SIZE]
            print(f"Embedding batch {idx // BATCH_SIZE + 1}: {len(batch)} texts")
            batch_embeddings = embedder.embed_batch(batch, batch_size=BATCH_SIZE)
            embeddings.extend(batch_embeddings)

    update_rows(rows, embeddings, args.dry_run)

    if not args.dry_run:
        with psycopg.connect(conninfo(), autocommit=True) as conn:
            conn.execute("VACUUM ANALYZE travel.poi;")
        print("Backfill complete.")


if __name__ == "__main__":
    main()
