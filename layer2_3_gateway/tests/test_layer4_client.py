"""P6: transport_modes mapping from LLM contract to Layer 4 payload."""
import pytest
from app.schemas.trip import LLMDataContract
from app.services.transport_modes import transport_modes_from_contract
from app.services.layer4_client import Layer4Client


@pytest.mark.parametrize(
    "walking_tolerance,expected",
    [
        ("low", ["taxi"]),
        ("medium", ["taxi", "walking"]),
        (None, ["taxi", "walking"]),
        ("high", ["walking", "taxi"]),
    ],
)
def test_transport_modes_from_contract(walking_tolerance, expected):
    contract = LLMDataContract(
        num_days=2,
        budget_max=1_000_000,
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        walking_tolerance=walking_tolerance,
    )
    assert transport_modes_from_contract(contract) == expected


def test_build_payload_uses_walking_tolerance():
    client = Layer4Client()
    contract = LLMDataContract(
        num_days=1,
        budget_max=500_000,
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin",
        walking_tolerance="low",
    )
    payload = client._build_payload([], contract)
    assert payload["constraints"]["transport_modes"] == ["taxi"]
    assert payload["constraints"]["budget_total"] == 500_000


def test_re_route_constraints_from_original_itinerary():
    client = Layer4Client()
    original = {
        "days": [
            {
                "day_index": 0,
                "hotel_name": "Hotel",
                "hotel_location": {"latitude": 16.46, "longitude": 107.59},
                "stops": [
                    {
                        "poi_id": "poi-1",
                        "poi_name": "Test",
                        "location": {"latitude": 16.47, "longitude": 107.58},
                        "visit_duration_min": 60,
                    }
                ],
            }
        ],
        "constraints": {"transport_modes": ["taxi"]},
    }
    payload_constraints = client._re_route_constraints(original, day_index=0)
    assert payload_constraints["transport_modes"] == ["taxi"]
