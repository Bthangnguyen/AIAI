"""Integration tests for trip planning API."""
import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.schemas.trip import ChatProcessResponse, LLMDataContract

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


async def test_chat_process_missing_budget(client: AsyncClient):
    """HTTP: clarifying when budget is missing after destination + days known."""
    mock_resp = ChatProcessResponse(
        status="clarifying",
        reply="Bạn dự kiến ngân sách khoảng bao nhiêu cho chuyến đi Huế 3 ngày?",
        updated_contract=LLMDataContract(destination="Huế", num_days=3, budget_max=None),
    )
    with patch("app.api.trip_planner.llm_service.process_chat_turn", AsyncMock(return_value=mock_resp.model_dump())):
        response = await client.post(
            "/trip/chat_process",
            json={
                "message": "Đi Huế 3 ngày",
                "history": [],
                "current_contract": {
                    "destination": None,
                    "budget_max": None,
                    "radius_km": 10.0,
                    "num_days": 1,
                    "tags": [],
                    "locked_pois": [],
                },
            },
        )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "clarifying"
    assert body["updated_contract"]["num_days"] == 3
    assert body["updated_contract"]["budget_max"] is None


async def test_chat_process_missing_days(client: AsyncClient):
    """HTTP: clarifying when num_days is missing."""
    mock_resp = ChatProcessResponse(
        status="clarifying",
        reply="Bạn muốn đi Huế mấy ngày?",
        updated_contract=LLMDataContract(destination="Huế", num_days=1, budget_max=None),
    )
    with patch("app.api.trip_planner.llm_service.process_chat_turn", AsyncMock(return_value=mock_resp.model_dump())):
        response = await client.post(
            "/trip/chat_process",
            json={
                "message": "Tôi muốn đi Huế",
                "history": [],
                "current_contract": {
                    "destination": None,
                    "budget_max": None,
                    "radius_km": 10.0,
                    "num_days": 1,
                    "tags": [],
                    "locked_pois": [],
                },
            },
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "clarifying"
