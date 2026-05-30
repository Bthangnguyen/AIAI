from app.schemas.trip import LLMDataContract
from app.services.layer4_client import Layer4Client


def test_layer4_payload_uses_afternoon_time_slot_without_explicit_window():
    contract = LLMDataContract(
        destination="Huế",
        num_days=1,
        budget_max=500000,
        time_window=None,
        time_slot="afternoon",
    )

    payload = Layer4Client()._build_payload([], contract)

    assert payload["day_plans"][0]["start_time_min"] == 780
    assert payload["day_plans"][0]["end_time_min"] == 1080


def test_layer4_payload_explicit_time_window_overrides_slot():
    contract = LLMDataContract(
        destination="Huế",
        num_days=1,
        budget_max=500000,
        time_slot="afternoon",
        time_window={"start_min": 840, "end_min": 1020},
    )

    payload = Layer4Client()._build_payload([], contract)

    assert payload["day_plans"][0]["start_time_min"] == 840
    assert payload["day_plans"][0]["end_time_min"] == 1020


def test_layer4_payload_clamps_afternoon_start_to_13h():
    contract = LLMDataContract(
        destination="Huế",
        num_days=1,
        budget_max=500000,
        time_slot="afternoon",
        time_window={"start_min": 720, "end_min": 1080},
    )

    payload = Layer4Client()._build_payload([], contract)

    assert payload["day_plans"][0]["start_time_min"] == 780
    assert payload["day_plans"][0]["end_time_min"] == 1080
