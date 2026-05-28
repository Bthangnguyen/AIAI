"""TDD verification: prompt contract and pure functions (no live LLM)."""
from app.services.llm_extractor import SYSTEM_PROMPT, CHAT_PROCESS_SYSTEM_PROMPT, LLMExtractorService
from app.services.transport_modes import transport_modes_from_contract
from app.schemas.trip import LLMDataContract


def test_system_prompt_documents_walking_tolerance():
    assert "walking_tolerance" in SYSTEM_PROMPT


def test_chat_process_prompt_documents_walking_tolerance():
    assert "walking_tolerance" in CHAT_PROCESS_SYSTEM_PROMPT


def test_walking_slang_maps_to_taxi_only_transport():
    contract = LLMDataContract(destination="Huế", num_days=2, budget_max=1_000_000, walking_tolerance="low")
    assert contract.walking_tolerance == "low"
    assert transport_modes_from_contract(contract) == ["taxi"]
