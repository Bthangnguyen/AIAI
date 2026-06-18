from app.schemas.trip import LLMDataContract, PartySpec, TransportPlanSpec
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


def test_solo_needs_transport_prefers_motorbike_hailing_over_taxi():
    contract = LLMDataContract(
        destination="Hue",
        num_days=1,
        budget_max=500_000,
        transport_policy="system_suggest_per_leg",
        party=PartySpec(size=1, type="solo"),
        transport_plan=TransportPlanSpec(
            availability="needs_transport",
            primary_mode="mixed",
            fallback_mode="taxi",
            cost_policy="per_leg",
        ),
    )

    result = CostEstimatorService().enrich(_sample_itinerary(1), contract)

    modes = [leg["mode"] for leg in result["days"][0]["transport_legs"] if leg["distance_km"] > 1]
    assert modes
    assert set(modes) == {"motorbike_hailing"}


def test_transport_distance_supports_lat_lng_location_aliases():
    itinerary = _sample_itinerary(1)
    itinerary["days"][0]["start_hotel_location"] = {"lat": 16.4637, "lng": 107.5905}
    itinerary["days"][0]["end_hotel_location"] = {"lat": 16.4637, "lng": 107.5905}
    itinerary["days"][0]["stops"][0]["location"] = {"lat": 16.469, "lng": 107.577}

    contract = LLMDataContract(destination="Hue", num_days=1, budget_max=500_000)
    result = CostEstimatorService().enrich(itinerary, contract)

    assert result["days"][0]["transport_legs"][0]["distance_km"] > 0
    assert result["days"][0]["transport_legs"][0]["distance_confidence"] == "high"


def test_each_day_adds_return_leg_to_lodging():
    contract = LLMDataContract(
        destination="Hue",
        num_days=2,
        budget_max=1_000_000,
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Hue Hotel",
    )

    result = CostEstimatorService().enrich(_sample_itinerary(2), contract)

    first_day_legs = result["days"][0]["transport_legs"]
    assert first_day_legs[-1]["is_return_to_lodging"] is True
    assert first_day_legs[-1]["to_name"] == "Hue Hotel"
    assert first_day_legs[-1]["distance_km"] > 0


def test_group_budget_defaults_per_person_and_shared_homestay_cost():
    contract = LLMDataContract(
        destination="Hue",
        num_days=3,
        budget_max=1_000_000,
        budget_unit_scope="per_person",
        party=PartySpec(size=3, type="friends"),
        group_size=3,
        hotel_name="Budget Homestay",
        lodging_preference=["homestay"],
        lodging_budget_per_night=500_000,
    )

    result = CostEstimatorService().enrich(_sample_itinerary(3), contract)

    summary = result["cost_summary"]
    assert summary["party_size"] == 3
    assert summary["budget_per_person"] == 1_000_000
    assert summary["group_budget_total"] == 3_000_000
    assert result["lodging_plan"]["room_capacity"] == 4
    assert result["lodging_plan"]["total_cost"] == 1_000_000
    assert result["lodging_plan"]["per_person_cost"] == 333_333
    assert summary["per_person_cost"] == round(summary["group_total_cost"] / 3)


def test_cost_estimator_reinterprets_non_explicit_group_budget_for_group_trip():
    contract = LLMDataContract(
        destination="Hue",
        num_days=3,
        budget_max=1_000_000,
        budget_unit_scope="group_total",
        budget_scope_evidence="Solo or no group size; per-person and group-total are equivalent.",
        party=PartySpec(size=3, type="friends"),
        group_size=3,
    )

    result = CostEstimatorService().enrich(_sample_itinerary(3), contract)

    summary = result["cost_summary"]
    assert summary["budget_unit_scope"] == "per_person"
    assert summary["budget_per_person"] == 1_000_000
    assert summary["group_budget_total"] == 3_000_000


def test_two_person_budget_transport_compares_taxi_and_motorbike_hailing():
    itinerary = _sample_itinerary(1)
    itinerary["days"][0]["stops"] = [
        {
            "poi_id": "far-food",
            "poi_name": "Far Local Food",
            "category": "food",
            "location": {"latitude": 16.55, "longitude": 107.68},
            "price": 60_000,
            "entrance_fee": 0,
        }
    ]
    contract = LLMDataContract(
        destination="Hue",
        num_days=1,
        budget_max=500_000,
        budget_unit_scope="per_person",
        party=PartySpec(size=2, type="couple"),
        group_size=2,
        transport_policy="system_suggest_per_leg",
        transport_plan=TransportPlanSpec(availability="needs_transport", primary_mode="mixed"),
    )

    result = CostEstimatorService().enrich(itinerary, contract)

    paid_legs = [leg for leg in result["days"][0]["transport_legs"] if leg["distance_km"] > 1]
    assert paid_legs
    assert all(leg["vehicles_needed"] >= 1 for leg in paid_legs)
    assert {leg["mode"] for leg in paid_legs}.issubset({"taxi", "motorbike_hailing"})


def test_virtual_rest_stop_does_not_create_zero_transport_leg():
    itinerary = _sample_itinerary(1)
    itinerary["days"][0]["stops"].insert(
        1,
        {
            "poi_id": "__rest_break__",
            "poi_name": "Rest",
            "category": "rest",
            "visit_duration_min": 30,
            "arrival_time_min": 600,
        },
    )
    contract = LLMDataContract(destination="Hue", num_days=1, budget_max=500_000)

    result = CostEstimatorService().enrich(itinerary, contract)

    rest = result["days"][0]["stops"][1]
    assert "transport_from_prev" not in rest
    assert all(leg["distance_km"] > 0 for leg in result["days"][0]["transport_legs"])


def test_virtual_meal_stop_with_location_does_not_create_transport_cost():
    itinerary = _sample_itinerary(1)
    itinerary["days"][0]["stops"].insert(
        1,
        {
            "poi_id": "__meal_lunch__",
            "poi_name": "Ăn trưa / nghỉ ngơi",
            "category": "meal_break",
            "location": {"latitude": 16.52, "longitude": 107.65},
            "visit_duration_min": 45,
            "arrival_time_min": 715,
        },
    )
    contract = LLMDataContract(destination="Hue", num_days=1, budget_max=500_000)

    result = CostEstimatorService().enrich(itinerary, contract)

    meal = result["days"][0]["stops"][1]
    assert "transport_from_prev" not in meal
    assert "transport_cost_from_prev" not in meal
    assert all(leg["to_stop_id"] != "__meal_lunch__" for leg in result["days"][0]["transport_legs"])
