from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings as global_settings

# AsyncSessionFactory with bounded pool
engine = create_async_engine(
    global_settings.sql_url.unicode_string(),
    pool_size=global_settings.DB_POOL_MIN_SIZE,
    max_overflow=global_settings.DB_POOL_MAX_SIZE - global_settings.DB_POOL_MIN_SIZE,
    pool_timeout=global_settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Detect stale connections
    echo=False,  # Turn off echo in production
)

AsyncSessionFactory = async_sessionmaker(
    engine, autoflush=False, expire_on_commit=False
)
