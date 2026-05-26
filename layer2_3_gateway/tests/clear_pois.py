"""Quick script to clear old POI data and re-run ingestion."""
import asyncio
from app.config import settings
from psycopg_pool import AsyncConnectionPool

async def clear():
    pool = AsyncConnectionPool(settings.get_conn_str())
    await pool.open()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM travel.poi;")
            print("🗑️ Cleared all existing POI data")
            await cur.execute("SELECT COUNT(*) FROM travel.poi;")
            print(f"   Rows remaining: {(await cur.fetchone())[0]}")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(clear())
