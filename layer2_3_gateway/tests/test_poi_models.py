import pytest
from app.schemas.trip import LLMDataContract, POIResponse, TripPlanRequest

def test_llm_data_contract_defaults():
    c = LLMDataContract(hotel_lat=16.46, hotel_lon=107.59)
    assert c.radius_km == 10.0
    assert c.num_days == 1
    assert c.tags == []
    assert c.locked_pois == []
    assert c.hotel_name == "Hotel"

def test_llm_data_contract_full():
    c = LLMDataContract(
        budget_max=2000000, radius_km=15, num_days=3,
        tags=["culture", "street_food"],
        locked_pois=["Đại Nội Huế", "Lăng Tự Đức"],
        weather_preference="indoor",
        hotel_lat=16.4637, hotel_lon=107.5905,
        hotel_name="Century Riverside"
    )
    assert len(c.locked_pois) == 2
    assert c.budget_max == 2000000
    assert c.hotel_name == "Century Riverside"

def test_trip_plan_request_required_fields():
    r = TripPlanRequest(
        user_prompt="Tôi muốn đi Huế 3 ngày",
        hotel_lat=16.46, hotel_lon=107.59, num_days=3,
    )
    assert r.num_days == 3
    assert r.user_prompt == "Tôi muốn đi Huế 3 ngày"
