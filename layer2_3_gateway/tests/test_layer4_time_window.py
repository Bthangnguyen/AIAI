import pytest
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


@pytest.mark.anyio
async def test_layer4_empty_itinerary_converts_to_error():
    import pytest
    from unittest.mock import patch, AsyncMock
    
    client = Layer4Client()
    mock_response = {
        "status": "success",
        "days": [
            {
                "day_index": 0,
                "stops": [
                    {
                        "poi_id": "hotel_day_0",
                        "poi_name": "Hotel",
                        "arrival_time_min": 480,
                        "departure_time_min": 500,
                    }
                ]
            }
        ]
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        # We need mock_post to return a response with status_code=200, json() returning mock_response
        mock_response_obj = AsyncMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json = lambda: mock_response
        mock_response_obj.raise_for_status = lambda: None
        mock_post.return_value = mock_response_obj
        
        result = await client.plan(
            pois=[],
            contract=LLMDataContract(destination="Huế", num_days=1)
        )
        
        assert result["error_code"] == "INFEASIBLE_CONSTRAINT"
        assert "bớt điểm" in result["message"]

