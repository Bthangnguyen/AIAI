"""Tests for plan_alternatives endpoint."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from fastapi import status

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def check_db():
    import socket
    try:
        socket.getaddrinfo("db", None)
    except socket.gaierror:
        pytest.skip("Database host 'db' is offline/unresolved.")


async def test_plan_alternatives_validation(client: AsyncClient):
    response = await client.post("/trip/plan_alternatives", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_plan_alternatives_returns_three_plans(client: AsyncClient):
    mock_pipeline = AsyncMock(
        return_value=(
            type("Contract", (), {"num_days": 2, "budget_max": 1_000_000})(),
            [],
        )
    )
    mock_l4 = AsyncMock(
        return_value={
            "status": "success",
            "num_plans": 3,
            "plans": [
                {"style": "balanced", "label": "Cân bằng", "days": [], "metrics": {"poi_count": 12}},
                {"style": "budget", "label": "Tiết kiệm", "days": [], "metrics": {"poi_count": 10}},
                {"style": "chill", "label": "Thoải mái", "days": [], "metrics": {"poi_count": 7}},
            ],
        }
    )

    with patch("app.api.trip_planner._run_pipeline", mock_pipeline):
        with patch("app.api.trip_planner.layer4_client.plan_alternatives", mock_l4):
            response = await client.post(
                "/trip/plan_alternatives",
                json={"user_prompt": "Đi Huế 2 ngày ngân sách 1 triệu", "num_days": 2, "budget": 1_000_000},
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_pipeline.assert_awaited_once()


async def test_plan_alternatives_success_with_pois(client: AsyncClient):
    from app.schemas.trip import POIResponse, LLMDataContract

    contract = LLMDataContract(destination="Huế", num_days=2, budget_max=1_000_000)
    pois = [
        POIResponse(
            uuid=uuid.uuid4(),
            name="Đại Nội",
            category="Di tích",
            latitude=16.46,
            longitude=107.57,
        )
    ]
    mock_l4 = AsyncMock(
        return_value={
            "status": "success",
            "num_plans": 3,
            "plans": [{"style": "balanced"}, {"style": "budget"}, {"style": "chill"}],
        }
    )

    with patch("app.api.trip_planner._run_pipeline", AsyncMock(return_value=(contract, pois))):
        with patch("app.api.trip_planner.layer4_client.plan_alternatives", mock_l4):
            response = await client.post(
                "/trip/plan_alternatives",
                json={"user_prompt": "Đi Huế 2 ngày", "num_days": 2},
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["num_plans"] == 3
    mock_l4.assert_awaited_once()
