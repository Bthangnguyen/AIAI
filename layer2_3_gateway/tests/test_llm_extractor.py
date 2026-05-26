"""Tests for Layer 2 LLM intent extraction."""
import pytest
from app.schemas.trip import LLMDataContract
from app.services.llm_extractor import LLMExtractorService, SYSTEM_PROMPT


def test_system_prompt_exists():
    assert "locked_pois" in SYSTEM_PROMPT
    assert "budget_max" in SYSTEM_PROMPT


def test_fallback_contract():
    """When LLM fails, service should return a safe fallback."""
    contract = LLMDataContract(
        hotel_lat=16.46, hotel_lon=107.59,
        hotel_name="Saigon Morin", num_days=2, tags=["general"],
    )
    assert contract.budget_max is None
    assert contract.radius_km == 10.0
    assert contract.locked_pois == []


def test_service_init():
    """Service can be instantiated without API key."""
    service = LLMExtractorService()
    assert service._client is None


@pytest.mark.integration
@pytest.mark.anyio
async def test_process_chat_turn_extraction():
    service = LLMExtractorService()
    current = LLMDataContract(destination=None, num_days=1, budget_max=None, tags=[])
    res = await service.process_chat_turn(
        message="Tôi muốn đi Huế 3 ngày ngân sách 1 triệu",
        history=[],
        current_contract=current
    )
    assert res["status"] in ("clarifying", "ready")
    assert res["updated_contract"].destination == "Huế"
    assert res["updated_contract"].num_days == 3

