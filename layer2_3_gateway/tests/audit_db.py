import asyncio
import sys
from app.config import settings
from psycopg_pool import AsyncConnectionPool

async def audit():
    pool = AsyncConnectionPool(settings.get_conn_str())
    await pool.open()
    
    output_lines = []
    def log(msg):
        output_lines.append(msg)
        
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 1. Count total POIs
            await cur.execute("SELECT COUNT(*) FROM travel.poi;")
            total = (await cur.fetchone())[0]
            log(f"=== TOTAL POIs: {total} ===\n")
            
            # 2. List all POIs with key fields
            await cur.execute("""
                SELECT uuid, name, category, visit_duration_min, 
                       price, entrance_fee, open_time, close_time, 
                       priority_score, tags, is_outdoor,
                       ST_AsText(coordinates) as coords
                FROM travel.poi
                ORDER BY priority_score DESC;
            """)
            rows = await cur.fetchall()
            for r in rows:
                log(f"  [{r[2]:10s}] {r[1]:25s} | dur={r[3]}min | fee={r[5]:>8.0f} | open={r[6]}-{r[7]} | prio={r[8]:.2f} | outdoor={r[9]} | tags={r[10]}")
                log(f"              coords: {r[11]}")
            
            # 3. Check schema
            log("\n=== TABLE SCHEMA ===")
            await cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'poi' AND table_schema = 'travel'
                ORDER BY ordinal_position;
            """)
            cols = await cur.fetchall()
            for c in cols:
                log(f"  {c[0]:25s} | {c[1]:20s} | null={c[2]}")
            
            # 4. Check indexes
            log("\n=== INDEXES ===")
            await cur.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'poi' AND schemaname = 'travel';
            """)
            idxs = await cur.fetchall()
            for idx in idxs:
                log(f"  {idx[0]}")
                
    await pool.close()
    
    # Save output to a UTF-8 file
    with open("tests/poi_dump.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("\nSaved dump to tests/poi_dump.txt successfully.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(audit())

