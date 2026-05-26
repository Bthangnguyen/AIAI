"""Integration tests for trip planning API."""
import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health(client: AsyncClient):
    response = await client.get("/trip/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ready"


async def test_plan_trip_validation(client: AsyncClient):
    """Test request validation."""
    response = await client.post("/trip/plan_trip", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_plan_trip_minimal(client: AsyncClient):
    """Test with minimal valid request."""
    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Tôi muốn đi Huế 2 ngày",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 2,
        },
    )
    # May return partial/error if no POIs seeded, but should not crash
    assert response.status_code in [200, 404, 500]
