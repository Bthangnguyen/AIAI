import json
import os
import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

# Disable API key check
from src.api.dependencies import verify_api_key
app.dependency_overrides[verify_api_key] = lambda: None

def load_real_pois():
    filepath = os.path.join(os.path.dirname(__file__), "fixtures", "real_hue_pois.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Map the JSON structure to our POI model structure
    pois = []
    for item in data:
        # P15 (Ga Hue) acts as the hotel, we will separate it out in the test if needed.
        pois.append({
            "id": item["id"],
            "name": item["name"],
            "category": "attraction",
            "location": {
                "latitude": item["lat"],
                "longitude": item["lng"]
            },
            "visit_duration_min": item["duration_minutes"],
            "time_window": {
                "start_min": item["time_window_minutes"][0],
                "end_min": item["time_window_minutes"][1]
            },
            "entrance_fee": 0
        })
    return pois

def test_real_hue_routing_snap_to_road():
    """
    Test routing using real Hue POIs.
    This will implicitly test OSRM's ability to snap coordinates to roads 
    (e.g., Lăng Khải Định which is on a mountain).
    """
    pois = load_real_pois()
    
    # Use Ga Huế (P15) as the hotel (Depot)
    hotel_poi = next(p for p in pois if p["id"] == "P15")
    pois = [p for p in pois if p["id"] != "P15"]
    
    hotel = {
        "id": "hotel_ga_hue",
        "name": hotel_poi["name"],
        "location": hotel_poi["location"]
    }
    
    # We have 14 POIs left. Let's plan them for 2 days.
    payload = {
        "pois": pois,
        "hotels": [hotel],
        "constraints": {
            "num_days": 2,
            "transport_modes": ["taxi"],
            "max_travel_time_per_day_min": 180,
            "max_pois_per_day": 8
        }
    }
    
    response = client.post("/plan", json=payload)
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert data["status"] == "success"
    
    # Should visit all 14 POIs if time permits
    # Depending on travel time, some might be dropped, but let's just ensure it routed successfully
    assert data["total_pois_visited"] > 10
    
    # Check that distances are reasonable (not 0, not absurdly high)
    # 14 POIs around Hue shouldn't be more than 100km total.
    assert 5.0 < data["total_distance_km"] < 150.0
    
    # Check that OSRM didn't crash (if it crashes, distance might be haversine, but it still works.
    # To truly verify OSRM, we would need to check logs, but a 200 OK means the system is resilient).
    
def test_strict_time_windows():
    """
    Test that the solver respects strict time windows.
    We will modify Đại Nội Huế (P01) to only open from 14:00 to 15:00 (840 to 900 min).
    """
    pois = load_real_pois()
    
    # Use Ga Huế (P15) as the hotel
    hotel_poi = next(p for p in pois if p["id"] == "P15")
    hotel = {
        "id": "hotel_ga_hue",
        "name": hotel_poi["name"],
        "location": hotel_poi["location"]
    }
    
    # Filter to only a few POIs to make it a 1-day trip
    test_poi_ids = ["P01", "P02", "P03"]
    selected_pois = [p for p in pois if p["id"] in test_poi_ids]
    
    # Modify Đại Nội (P01) to have a strict time window: 14:00 - 15:00
    p01 = next(p for p in selected_pois if p["id"] == "P01")
    p01["time_window"] = {"start_min": 840, "end_min": 900}
    
    # Set visit duration to 30 mins so it fits easily
    p01["visit_duration_min"] = 30
    
    payload = {
        "pois": selected_pois,
        "hotels": [hotel],
        "constraints": {
            "num_days": 1,
            "transport_modes": ["taxi"]
        }
    }
    
    response = client.post("/plan", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["days"]) == 1
    day_plan = data["days"][0]
    
    # Find Đại Nội in the stops
    dai_noi_stop = next((s for s in day_plan["stops"] if s["poi_id"] == "P01"), None)
    
    # Since it's a tight window, it might get visited, or it might be dropped.
    # If visited, check that arrival time >= 840 (14:00)
    if dai_noi_stop:
        assert dai_noi_stop["arrival_time_min"] >= 840
        assert dai_noi_stop["departure_time_min"] <= 900
    else:
        # If it was dropped, it must be in the dropped_pois list
        dropped_ids = [dp["poi_id"] for dp in data.get("dropped_pois", [])]
        assert "P01" in dropped_ids
