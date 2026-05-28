"""P6: walking_tolerance failsafe and comfort scoring."""
import pytest
from app.schemas.trip import LLMDataContract, POIResponse
from app.services.llm_extractor import LLMExtractorService
from app.services.utility_scorer import UtilityScorer
from uuid import uuid4


@pytest.fixture
def service():
    return LLMExtractorService()


def test_failsafe_low_walking_from_slang(service):
    contract = LLMDataContract(destination="Huế", num_days=2, budget_max=1_000_000, walking_tolerance="low")
    assert contract.walking_tolerance == "low"


def test_failsafe_high_walking_from_slang(service):
    contract = LLMDataContract(destination="Huế", num_days=2, budget_max=1_000_000, walking_tolerance="high")
    assert contract.walking_tolerance == "high"


def test_comfort_penalizes_walking_pois_when_tolerance_low():
    scorer = UtilityScorer()
    contract = LLMDataContract(walking_tolerance="low")
    walking_poi = POIResponse(
        uuid=uuid4(),
        name="Phố đi bộ",
        category="outdoor",
        latitude=16.46,
        longitude=107.59,
        tags=["walking", "outdoor"],
        visit_duration_min=90,
    )
    cafe_poi = POIResponse(
        uuid=uuid4(),
        name="Cafe",
        category="cafe",
        latitude=16.46,
        longitude=107.59,
        tags=["cafe"],
        visit_duration_min=45,
    )
    walking_score = scorer._compute_comfort(walking_poi, contract)
    cafe_score = scorer._compute_comfort(cafe_poi, contract)
    assert walking_score < cafe_score


def test_budget_fit_penalizes_expensive_poi_for_low_budget():
    scorer = UtilityScorer()
    contract = LLMDataContract(budget_max=300_000)
    expensive = POIResponse(
        uuid=uuid4(),
        name="Lăng",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        entrance_fee=200_000,
    )
    cheap = POIResponse(
        uuid=uuid4(),
        name="Chùa",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        entrance_fee=0,
    )
    assert scorer._compute_budget_fit(expensive, contract) < scorer._compute_budget_fit(cheap, contract)
