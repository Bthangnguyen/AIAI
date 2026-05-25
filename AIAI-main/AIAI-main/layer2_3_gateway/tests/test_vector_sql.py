"""Test semantic vector search with 'weird' user inputs.

Sends Vietnamese queries to pgvector via local sentence-transformers
to measure cosine distance against all 61 POIs.
"""
import asyncio
import os
import sys
import numpy as np
from sqlalchemy import text
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import AsyncSessionFactory

MODEL = None  # lazy-load singleton

def get_model():
    global MODEL
    if MODEL is None:
        MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return MODEL

def embed_query(query: str) -> str:
    """Embed query text and pad to 1536-dim for pgvector."""
    model = get_model()
    emb = model.encode([query])[0]
    vec = np.zeros(1536)
    vec[:384] = emb
    return str(vec.tolist())


async def search(query: str, limit: int = 15):
    """Run a single semantic search and print results."""
    vec_str = embed_query(query)

    sql = text("""
        SELECT name, category, tags, description,
               (tags_vector <=> CAST(:vec AS vector)) as distance
        FROM travel.poi
        ORDER BY tags_vector <=> CAST(:vec AS vector)
        LIMIT :lim;
    """)

    async with AsyncSessionFactory() as session:
        result = await session.execute(sql, {"vec": vec_str, "lim": limit})
        rows = result.fetchall()

    print(f"\n{'#':<3} {'POI Name':<35} {'Category':<14} {'Dist':<8} Tags")
    print("─" * 100)
    for i, (name, cat, tags, desc, dist) in enumerate(rows, 1):
        marker = ""
        # Highlight semantic "hits" for our weird queries
        name_lower = name.lower()
        tags_lower = str(tags).lower()
        if any(k in name_lower or k in tags_lower for k in
               ["boat", "thuyền", "river", "voi", "arena", "fight", "đấu"]):
            marker = " ⭐"
        print(f"{i:<3} {name:<35} {cat:<14} {dist:.4f}  {tags}{marker}")


async def main():
    print("=" * 100)
    print("🧪 SEMANTIC VECTOR SEARCH — 'Kịch bản dở hơi' Test Suite")
    print("   Model: all-MiniLM-L6-v2 (384-dim, padded → 1536)")
    print("   DB: travel.poi (61 POIs), pgvector cosine distance (<=>)")
    print("=" * 100)

    # ─── Test 1: "đá gà, chèo thuyền" ───
    print("\n🔍 Query 1: 'đá gà, chèo thuyền'")
    print("   Expectation: 'Arena Trường Đấu Voi' + 'Sông Hương Boat Tour' should rank high")
    await search("đá gà, chèo thuyền")

    # ─── Test 2: Just "chèo thuyền" ───
    print("\n🔍 Query 2: 'chèo thuyền trên sông' (boat/river specific)")
    print("   Expectation: Boat Tour, Đầm Chuồn, Phá Tam Giang should appear")
    await search("chèo thuyền trên sông")

    # ─── Test 3: Just "đá gà" ───
    print("\n🔍 Query 3: 'xem đá gà đấu vật' (animal fighting)")
    print("   Expectation: 'Arena Trường Đấu Voi' should rank higher")
    await search("xem đá gà đấu vật")

    # ─── Test 4: English equivalent ───
    print("\n🔍 Query 4: 'cockfighting arena rowing boat' (English)")
    print("   Expectation: Same semantic meaning, test cross-lingual")
    await search("cockfighting arena rowing boat")

    # ─── Test 5: Completely nonsense ───
    print("\n🔍 Query 5: 'mua bitcoin đào coin ăn phở' (total nonsense)")
    print("   Expectation: Results should have HIGH distance (>0.5), nothing relevant")
    await search("mua bitcoin đào coin ăn phở")

    # ─── Test 6: Exact match sanity check ───
    print("\n🔍 Query 6: 'temple pagoda spiritual zen' (exact tag match)")
    print("   Expectation: Chùa Thiên Mụ, Chùa Từ Hiếu, Chùa Huyền Không should rank top")
    await search("temple pagoda spiritual zen")


if __name__ == "__main__":
    asyncio.run(main())
