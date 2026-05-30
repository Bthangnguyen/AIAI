from uuid import uuid4

from app.api.trip_planner import _detect_required_micro_intents, _merge_required_micro_pois
from app.schemas.trip import LLMDataContract, POIResponse


def test_detects_required_micro_food_intents_from_prompt():
    contract = LLMDataContract(
        destination="Hue",
        food_preferences=["bun_bo", "com_hen", "che_hue", "cafe_muoi"],
    )

    required = _detect_required_micro_intents(
        contract,
        "Toi muon an bun bo, com hen, che Hue va cafe muoi",
    )

    assert required == ["bun_bo", "com_hen", "che_hue", "cafe_muoi"]


def test_generic_cafe_does_not_become_cafe_muoi_lock():
    contract = LLMDataContract(destination="Hue", tags=["cafe"])

    required = _detect_required_micro_intents(contract, "Di 2 quan cafe dep")

    assert "cafe_muoi" not in required


def _poi(name: str, tags: list[str], category: str = "food") -> POIResponse:
    return POIResponse(
        uuid=uuid4(),
        name=name,
        category=category,
        category_group=category,
        description=name,
        latitude=16.46,
        longitude=107.59,
        visit_duration_min=45,
        price=40000,
        entrance_fee=0,
        open_time=480,
        close_time=1260,
        priority_score=0.5,
        tags=tags,
    )


def test_merge_required_micro_pois_filters_duplicate_same_dish():
    locked_bun_bo = _poi("Bun Bo Locked", ["bun_bo", "street_food"])
    locked_bun_bo.is_locked = True
    duplicate_bun_bo = _poi("Another Bun Bo", ["bun_bo", "street_food"])
    com_hen = _poi("Com Hen", ["com_hen", "street_food"])

    merged = _merge_required_micro_pois(
        [duplicate_bun_bo, com_hen],
        [locked_bun_bo],
        target_count=10,
    )

    names = [p.name for p in merged]
    assert "Bun Bo Locked" in names
    assert "Another Bun Bo" not in names
    assert "Com Hen" in names
