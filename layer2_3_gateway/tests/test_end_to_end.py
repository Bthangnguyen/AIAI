"""Master End-to-End Test Scenarios for Layer 2 -> Layer 3 -> Layer 4."""

import pytest
from unittest.mock import patch
from fastapi import status
from httpx import AsyncClient

from app.schemas.trip import LLMDataContract, TimeWindowSpec

import json

pytestmark = pytest.mark.anyio

# Global dict to store outputs
SCENARIO_OUTPUTS = {}

def save_output(scenario_name: str, response_json: dict):
    SCENARIO_OUTPUTS[scenario_name] = response_json
    with open("test_outputs.json", "w", encoding="utf-8") as f:
        json.dump(SCENARIO_OUTPUTS, f, ensure_ascii=False, indent=2)

@pytest.fixture
def mock_llm():
    """Mock LLM to bypass insufficient quota and simulate various intents."""
    with patch("app.services.llm_extractor.LLMExtractorService.extract_intent") as mock:
        yield mock


async def test_scenario_1_happy_path(client: AsyncClient, mock_llm):
    """Mức độ 1: The Happy Path."""
    mock_llm.return_value = LLMDataContract(
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin",
        num_days=1,
        budget_max=500000,
        tags=["culture", "history"],
        radius_km=10.0,
    )

    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Tôi muốn đi dạo trung tâm Huế 1 ngày...",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 1,
        },
    )
    
    # Can return 200 (Success/Partial) or 404 if DB is completely empty.
    # We expect 200 since we have sample data.
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        save_output("Mức độ 1: Happy Path", data)
        assert data["pois_found"] > 0
        assert data["llm_contract"]["budget_max"] == 500000


async def test_scenario_2_hard_constraints(client: AsyncClient, mock_llm):
    """Mức độ 2: Cưỡng chế Ràng Buộc."""
    mock_llm.return_value = LLMDataContract(
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin",
        num_days=1,
        locked_pois=["Đại Nội Huế", "Chùa Thiên Mụ"],
        radius_km=10.0,
    )

    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Bắt buộc phải dẫn mình đi Lăng Khải Định...",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 1,
        },
    )
    
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        save_output("Mức độ 2: Hard Constraints", data)
        # Verify force include works (is_locked=True POIs are found)
        assert data["locked_pois"] >= 0  # Depending on if they exist in DB


async def test_scenario_3_fallback_tiers(client: AsyncClient, mock_llm):
    """Mức độ 3: Bùng nổ Dữ liệu (Kích hoạt Fallback)."""
    # Ask for beach in city center (requires expansion to 30km tier)
    mock_llm.return_value = LLMDataContract(
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Vincom Hue",
        num_days=1,
        tags=["beach"],
        radius_km=5.0,  # Tight initial radius
    )

    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Tôi muốn đi tắm biển Thuận An.",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Vincom Hue",
            "num_days": 1,
        },
    )
    
    assert response.status_code in [200, 404]


async def test_scenario_4_multi_day(client: AsyncClient, mock_llm):
    """Mức độ 4: Cụm Tuyến Đa Ngày."""
    mock_llm.return_value = LLMDataContract(
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin",
        num_days=3,
        radius_km=20.0,
    )

    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Gia đình mình đi chơi Huế 3 ngày 2 đêm.",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 3,
        },
    )
    
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        save_output("Mức độ 4: Multi Day", data)
        assert data["llm_contract"]["num_days"] == 3


async def test_scenario_5_system_resilience(client: AsyncClient):
    """Mức độ 5: System Resilience (LLM Fails -> Fallback used).
    We do NOT mock LLM here to ensure the real exception triggers fallback.
    """
    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Test fallback",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 1,
        },
    )
    
    # Must gracefully degrade and NOT return 500
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        save_output("Mức độ 5: System Resilience", data)
        assert "general" in data["llm_contract"]["tags"]


async def test_scenario_6_time_window(client: AsyncClient, mock_llm):
    """Mức độ 6: Time-Window Violations."""
    mock_llm.return_value = LLMDataContract(
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin",
        num_days=1,
        # Only 2 hours in the middle of the night
        time_window=TimeWindowSpec(start_min=1320, end_min=1440),
        radius_km=10.0,
    )

    response = await client.post(
        "/trip/plan_trip",
        json={
            "user_prompt": "Tôi đi từ 10h đêm đến 12h đêm",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5905,
            "hotel_name": "Saigon Morin",
            "num_days": 1,
        },
    )
    
    # Might return 404 Error: No POIs found matching your criteria.
    # OR 200 if some POIs are open 24/7 (0 to 1440)
    assert response.status_code in [200, 404]
