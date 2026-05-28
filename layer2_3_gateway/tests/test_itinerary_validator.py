"""Unit tests for post-solver LLM itinerary validator."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.schemas.trip import LLMDataContract, POIResponse
from app.services.itinerary_validator import ItineraryValidatorService, ItineraryValidationResponse, ItineraryAdjustment


@pytest.mark.anyio
async def test_itinerary_validation_and_adjustments():
    # 1. Create candidate POIs
    poi_keep = POIResponse(
        uuid=uuid4(),
        name="Chùa Thiên Mụ",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        tags=["temple", "spiritual"],
        visit_duration_min=60,
    )
    
    poi_remove = POIResponse(
        uuid=uuid4(),
        name="Chùa Từ Hiếu (Redundant)",
        category="culture",
        latitude=16.43,
        longitude=107.55,
        tags=["temple", "spiritual"],
        visit_duration_min=60,
    )
    
    poi_add = POIResponse(
        uuid=uuid4(),
        name="Cà phê Sơn (Replacement)",
        category="cafe",
        latitude=16.46,
        longitude=107.58,
        tags=["cafe", "relax"],
        visit_duration_min=45,
    )

    all_pois = [poi_keep, poi_remove, poi_add]

    # 2. Mock l4_result proposed itinerary
    l4_result = {
        "status": "success",
        "num_days": 1,
        "days": [
            {
                "day_index": 0,
                "date": "day-0",
                "start_time_min": 480,
                "stops": [
                    {
                        "poi_id": str(poi_keep.uuid),
                        "poi_name": poi_keep.name,
                        "arrival_time_min": 495,
                        "departure_time_min": 555,
                        "visit_duration_min": 60,
                    },
                    {
                        "poi_id": str(poi_remove.uuid),
                        "poi_name": poi_remove.name,
                        "arrival_time_min": 570,
                        "departure_time_min": 630,
                        "visit_duration_min": 60,
                    }
                ]
            }
        ]
    }

    contract = LLMDataContract(destination="Huế")

    # 3. Setup mock LLM response
    mock_response = ItineraryValidationResponse(
        is_reasonable=False,
        overall_analysis="Proposed day is too repetitive with two temples in a row. Replacing second temple with a coffee stop.",
        adjustments=[
            ItineraryAdjustment(
                action="REMOVE",
                day_index=0,
                poi_id=str(poi_remove.uuid),
                reason="Remove duplicate temple fatigue"
            ),
            ItineraryAdjustment(
                action="ADD",
                day_index=0,
                poi_id=str(poi_add.uuid),
                insert_index=1,
                reason="Add relaxing coffee stop after first temple visit"
            )
        ]
    )

    # 4. Initialize service and inject mock client
    service = ItineraryValidatorService()
    
    mock_chat_completions = MagicMock()
    mock_chat_completions.create = AsyncMock(return_value=mock_response)
    
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = mock_chat_completions
    
    service._client = mock_client

    # 5. Run validation and adjustment
    adjusted_result = await service.validate_and_adjust(
        l4_result=l4_result,
        contract=contract,
        all_pois=all_pois
    )

    # 6. Verify result
    assert adjusted_result is not None
    day = adjusted_result["days"][0]
    stops = day["stops"]
    
    # Redundant temple should be removed, coffee stop should be added
    assert len(stops) == 2
    assert stops[0]["poi_id"] == str(poi_keep.uuid)
    assert stops[1]["poi_id"] == str(poi_add.uuid)
    assert stops[1]["poi_name"] == "Cà phê Sơn (Replacement)"

    # Verify sequential arrival and departure timings re-interpolation
    # Start time: 480
    # Stop 0 (Chùa Thiên Mụ): arrival = 480 + 15 = 495, departure = 495 + 60 = 555
    # Stop 1 (Cà phê Sơn): arrival = 555 + 15 = 570, departure = 570 + 45 = 615
    assert stops[0]["arrival_time_min"] == 495
    assert stops[0]["departure_time_min"] == 555
    assert stops[1]["arrival_time_min"] == 570
    assert stops[1]["departure_time_min"] == 615
    
    assert day["total_visit_min"] == 105  # 60 + 45
    assert day["num_pois"] == 2
