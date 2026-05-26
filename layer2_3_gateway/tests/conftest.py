
import pytest

from httpx import AsyncClient, ASGITransport
from psycopg_pool import AsyncConnectionPool

from app.config import settings as global_settings
from app.database import engine
from app.main import app
from app.models.base import Base


@pytest.fixture(
    scope="session",
    params=[
        pytest.param(("asyncio", {"use_uvloop": False}), id="asyncio"),
    ],
)
def anyio_backend(request):
    return request.param


@pytest.fixture(scope="session")
async def start_db():
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all, checkfirst=True)
    #     await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    # for AsyncEngine created in function scope, close and
    # clean-up pooled connections
    await engine.dispose()


@pytest.fixture(scope="session")
async def client(start_db) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver/v1",
        headers={"Content-Type": "application/json"},
    ) as test_client:
        _conninfo = global_settings.get_conn_str()
        app.async_pool = AsyncConnectionPool(conninfo=_conninfo)
        yield test_client
        await app.async_pool.close()


from unittest.mock import patch

@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service():
    """Mock EmbeddingService.aembed_text to prevent real network calls to OpenAI during tests."""
    with patch("app.services.embedding_service.EmbeddingService.aembed_text") as mock:
        # Return a 1536-dimensional mock vector
        mock.return_value = [0.0] * 1536
        yield mock

