"""Debug: test a single INSERT to find the exact error."""
import asyncio
import uuid
from app.config import settings
from psycopg_pool import AsyncConnectionPool

async def test_insert():
    pool = AsyncConnectionPool(settings.get_conn_str())
    await pool.open()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Test raw SQL insert
            await cur.execute("""
                INSERT INTO travel.poi
                    (uuid, name, category, description, coordinates,
                     visit_duration_min, price, entrance_fee,
                     open_time, close_time, tags, is_outdoor, priority_score)
                VALUES
                    (%s, %s, %s, %s,
                     ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                     %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()),
                'Test POI', 'test', 'Test description',
                107.5786, 16.4698,
                60, 0.0, 0.0, 480, 1260,
                ['culture', 'test'],
                False, 0.5
            ))
            print("✅ Raw INSERT succeeded!")
            
            await cur.execute("SELECT COUNT(*) FROM travel.poi;")
            print(f"   Total rows: {(await cur.fetchone())[0]}")
            
            # Clean up test row
            await cur.execute("DELETE FROM travel.poi WHERE name = 'Test POI';")
            print("   Test row cleaned up")
            
    await pool.close()

if __name__ == "__main__":
    asyncio.run(test_insert())
