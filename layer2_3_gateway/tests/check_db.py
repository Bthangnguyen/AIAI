import asyncio
from app.main import app
from app.config import settings
from psycopg_pool import AsyncConnectionPool

async def check_db():
    _conninfo = settings.get_conn_str()
    pool = AsyncConnectionPool(conninfo=_conninfo)
    await pool.open()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM poi;")
            count = await cur.fetchone()
            print(f"TOTAL POIS IN DB: {count[0]}")
            
    await pool.close()

if __name__ == "__main__":
    asyncio.run(check_db())
