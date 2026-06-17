from app.schemas.trip import LLMDataContract, TransportPlanSpec
from app.services.cost_estimator import CostEstimatorService


def _sample_itinerary(num_days: int = 3):
    days = []
    for idx in range(num_days):
        days.append(
            {
                "day_index": idx,
                "start_hotel_name": "Hue Hotel",
                "start_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "end_hotel_name": "Hue Hotel",
                "end_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "stops": [
                    {
                        "poi_id": f"culture-{idx}",
                        "poi_name": "Dai Noi Hue",
                        "category": "culture",
                        "location": {"latitude": 16.469, "longitude": 107.577},
                        "entrance_fee": 200000,
                        "price": 0,
                        "travel_time_from_prev_min": 10,
                    },
                    {
                        "poi_id": f"food-{idx}",
                        "poi_name": "Bun bo Hue",
                        "category": "food",
                        "location": {"latitude": 16.466, "longitude": 107.59},
                        "entrance_fee": 0,
                        "price": 60000,
                        "travel_time_from_prev_min": 8,
                    },
                ],
            }
        )
    return {"status": "success", "num_days": num_days, "days": days}


def test_one_day_trip_has_no_lodging_cost():
    contract = LLMDataContract(destination="Hue", num_days=1, budget_max=500000)
    result = CostEstimatorService().enrich(_sample_itinerary(1), contract)

    assert result["lodging_plan"]["nights"] == 0
    assert result["lodging_plan"]["total_cost"] == 0
    assert result["cost_summary"]["lodging_cost"] == 0
    assert result["cost_summary"]["estimated_total_cost"] > result["cost_summary"]["poi_ticket_cost"]


def test_three_day_trip_adds_two_lodging_nights_and_total_cost():
    contract = LLMDataContract(
        destination="Hue",
        num_days=3,
        budget_max=2_500_000,
        preferred_pace="chill",
        budget_scope="total_trip",
    )
    result = CostEstimatorService().enrich(_sample_itinerary(3), contract, hotel_fallback=True)

    assert result["lodging_plan"]["nights"] == 2
    assert result["lodging_plan"]["total_cost"] == 900_000
    assert result["days"][0]["overnight_stay"] is not None
    assert result["days"][1]["overnight_stay"] is not None
    assert result["days"][2]["overnight_stay"] is None
    assert result["cost_summary"]["local_transport_cost"] > 0
    assert result["cost_summary"]["estimated_total_cost"] == result["budget_used"]
    assert result["days"][0]["transport_legs"][0]["mode_label"]


def test_existing_user_lodging_excludes_lodging_cost():
    contract = LLMDataContract(
        destination="Hue",
        num_days=3,
        budget_max=1_000_000,
        has_lodging=True,
        budget_scope="excludes_hotel",
        hotel_name="My Hotel",
    )
    result = CostEstimatorService().enrich(_sample_itinerary(3), contract)

    assert result["lodging_plan"]["nights"] == 2
    assert result["lodging_plan"]["mode"] == "provided_by_user"
    assert result["lodging_plan"]["total_cost"] == 0
    assert result["cost_summary"]["lodging_cost"] == 0


def test_own_transport_keeps_time_but_zero_transport_cost():
    contract = LLMDataContract(
        destination="Hue",
        num_days=1,
        budget_max=500_000,
        transport_plan=TransportPlanSpec(
            availability="has_own_transport",
            primary_mode="motorbike",
            cost_policy="time_only",
        ),
    )
    result = CostEstimatorService().enrich(_sample_itinerary(1), contract)

    leg = result["days"][0]["transport_legs"][0]
    assert leg["travel_time_min"] > 0
    assert leg["transport_cost"] == 0
    assert result["cost_summary"]["local_transport_cost"] == 0
