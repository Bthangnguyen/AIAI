"""Tests for Layer 2 LLM intent extraction."""
from types import SimpleNamespace

import pytest
from app.schemas.trip import LLMDataContract, TimeWindowSpec
from app.services.llm_extractor import LLMExtractorService, SYSTEM_PROMPT


class FailingCompletions:
    async def create(self, *args, **kwargs):
        raise RuntimeError("LLM disabled for deterministic unit test")


def offline_service() -> LLMExtractorService:
    service = LLMExtractorService()
    service._client = SimpleNamespace(
        chat=SimpleNamespace(completions=FailingCompletions())
    )
    return service


def complete_contract(**overrides) -> LLMDataContract:
    data = dict(
        destination="Huế",
        num_days=3,
        budget_max=3_000_000,
        tags=["culture", "cafe"],
        preferred_pace="chill",
        walking_tolerance="medium",
        food_preferences=["vegetarian"],
        locked_pois=["Đại Nội"],
        avoid_tags=["crowded"],
        time_window=TimeWindowSpec(start_min=480, end_min=1260),
        transport_modes=["taxi", "walking"],
        group_type="couple",
        group_size=2,
        hotel_name="Hue Default Hotel",
        hotel_confirmed=True,
        default_hotel_ok=True,
        confirmed_fields=[
            "destination",
            "num_days",
            "budget",
            "interests",
            "pace",
            "walking",
            "food",
            "must_visit",
            "avoid",
            "time_window",
            "transport",
            "group",
            "hotel",
        ],
    )
    data.update(overrides)
    return LLMDataContract(**data)


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


@pytest.mark.anyio
async def test_process_chat_turn_extraction():
    service = offline_service()
    current = LLMDataContract(destination=None, num_days=1, budget_max=None, tags=[])
    res = await service.process_chat_turn(
        message="Tôi muốn đi Huế 3 ngày ngân sách 1 triệu",
        history=[],
        current_contract=current
    )
    assert res["status"] == "clarifying"
    assert res["phase"] == "collecting"
    assert res["updated_contract"].destination == "Huế"
    assert res["updated_contract"].num_days == 3
    assert res["missing_fields"]


@pytest.mark.anyio
async def test_incomplete_prompt_asks_follow_up_not_ready():
    service = offline_service()
    res = await service.process_chat_turn(
        message="Đi Huế 3 ngày",
        history=[],
        current_contract=LLMDataContract(),
    )
    assert res["status"] == "clarifying"
    assert res["phase"] == "collecting"
    assert res["requires_confirmation"] is False
    assert res["updated_contract"].ready_to_plan is False


@pytest.mark.anyio
async def test_complete_info_requires_confirmation_before_ready():
    service = offline_service()
    res = await service.process_chat_turn(
        message=(
            "Đi Huế 3 ngày ngân sách 3tr, thích văn hóa cafe ăn uống, "
            "chill, đi bộ vừa phải, ăn chay, phải đi Đại Nội, tránh chỗ đông, "
            "8h-21h, taxi đi bộ, đi 2 người, dùng khách sạn mặc định"
        ),
        history=[],
        current_contract=LLMDataContract(),
    )
    assert res["status"] == "clarifying"
    assert res["phase"] == "confirming"
    assert res["requires_confirmation"] is True
    assert res["missing_fields"] == []
    assert res["updated_contract"].ready_to_plan is False


@pytest.mark.anyio
async def test_confirmation_turn_returns_ready():
    service = offline_service()
    current = complete_contract(confirmation_pending=True, ready_to_plan=False)
    res = await service.process_chat_turn(
        message="ok tạo đi",
        history=[],
        current_contract=current,
    )
    assert res["status"] == "ready"
    assert res["phase"] == "ready"
    assert res["updated_contract"].ready_to_plan is True


@pytest.mark.anyio
async def test_non_hue_destination_asks_to_switch_to_hue():
    service = offline_service()
    res = await service.process_chat_turn(
        message="Paris 3 ngày",
        history=[],
        current_contract=LLMDataContract(destination="Paris", num_days=3),
    )
    assert res["status"] == "clarifying"
    assert res["phase"] == "collecting"
    assert res["missing_fields"] == ["destination"]


@pytest.mark.anyio
async def test_hotel_info_is_preserved_across_turns():
    service = offline_service()
    current = LLMDataContract(
        destination="Huế",
        hotel_lat=16.4,
        hotel_lon=107.5,
        hotel_name="Mora",
        hotel_confirmed=True,
        confirmed_fields=["destination", "hotel"],
    )
    res = await service.process_chat_turn(
        message="Đi 2 ngày ngân sách 1tr",
        history=[],
        current_contract=current,
    )
    assert res["updated_contract"].hotel_lat == 16.4
    assert res["updated_contract"].hotel_lon == 107.5
    assert res["updated_contract"].hotel_name == "Mora"


@pytest.mark.anyio
async def test_post_plan_message_is_edit_intent():
    service = offline_service()
    res = await service.process_chat_turn(
        message="thêm cafe muối",
        history=[],
        current_contract=complete_contract(),
        has_draft=True,
    )
    assert res["phase"] == "editing"
    assert res["edit_intent"].action == "add_place"
